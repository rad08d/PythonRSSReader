#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""core - APT based installer using the PackageKit DBus interface"""
# Copyright (C) 2008-2009 Sebastian Heinlein <devel@glatzor.de>
# Copyright (C) 2009 Richard Hughes <richard@hughsie.com>
# Copyright (C) 2008 Sebastian Dröge <sebastian.droege@collabora.co.uk>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

__author__  = "Sebastian Heinlein <devel@glatzor.de>"
__state__   = "experimental"

from ConfigParser import ConfigParser
import functools
import locale
import logging
import os
import re
import subprocess
import time

import apt
import apt.debfile
import apt_pkg
from aptdaemon.policykit1 import get_pid_from_dbus_name
from defer import Deferred, defer, inline_callbacks, return_value
from defer.utils import dbus_deferred_method
import dbus
import dbus.service
import dbus.mainloop.glib
from gettext import gettext as _
import gettext
from gi.repository import Gio
from gi.repository import GObject
from gi.repository import Gst
from gi.repository import Gtk
from gi.repository import Pango
from xdg.DesktopEntry import DesktopEntry
from xdg.Exceptions import ParsingError

import utils
import errors

_backend_env = os.getenv("SESSIONINSTALLER_BACKEND", "aptdaemon")
if _backend_env == "synaptic":
    from backends.synaptic import SynapticBackend as Backend
elif _backend_env == "aptdaemon":
    from backends.aptd import AptDaemonBackend as Backend
else:
    from backends.dummy import DummyBackend as Backend


gettext.textdomain("sessioninstaller")
gettext.bindtextdomain("sessioninstaller")

dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

PACKAGEKIT_QUERY_DBUS_INTERFACE = "org.freedesktop.PackageKit.Query"
PACKAGEKIT_MODIFY_DBUS_INTERFACE = "org.freedesktop.PackageKit.Modify"
PACKAGEKIT_DBUS_PATH = "/org/freedesktop/PackageKit"
PACKAGEKIT_DBUS_SERVICE = "org.freedesktop.PackageKit"

INTERACT_NEVER = 0
INTERACT_CONFIRM_SEARCH = 1
INTERACT_CONFIRM_DEPS = 2
INTERACT_CONFIRM_INSTALL = 4
INTERACT_PROGRESS = 8
INTERACT_FINISHED = 16
INTERACT_WARNING = 32
INTERACT_UNKNOWN = 64
INTERACT_ALWAYS = 127

GSTREAMER_RECORD_MAP = {"encoder": "Gstreamer-Encoders",
                        "decoder": "Gstreamer-Decoders",
                        "urisource": "Gstreamer-Uri-Sources",
                        "urisink": "Gstreamer-Uri-Sinks",
                        "element": "Gstreamer-Elements"}

RESTRICTED_010_PACKAGES = ["gstreamer0.10-plugins-bad",
                           "gstreamer0.10-plugins-bad-multiverse",
                           "gstreamer0.10-ffmpeg",
                           "gstreamer0.10-plugins-ugly"]

RESTRICTED_10_PACKAGES = ["gstreamer1.0-plugins-bad",
                          "gstreamer1.0-libav",
                          "gstreamer1.0-plugins-ugly"]

GSTREAMER_010_SCORING = {"gstreamer0.10-plugins-good": 100,
                         "gstreamer0.10-fluendo-mp3": 90,
                         "gstreamer0.10-ffmpeg": 79,
                         "gstreamer0.10-plugins-ugly": 80,
                         "gstreamer0.10-plugins-bad": 70,
                         "gstreamer0.10-plugins-bad-multiverse": 60}

GSTREAMER_10_SCORING = {"gstreamer1.0-plugins-good": 100,
#                        "gstreamer1.0-fluendo-mp3": 90,
                        "gstreamer1.0-libav": 79,
                        "gstreamer1.0-plugins-ugly": 80,
                        "gstreamer1.0-plugins-bad": 70}


logging.basicConfig(format="%(levelname)s:%(message)s")
log = logging.getLogger("sessioninstaller")

(COLUMN_NAME,
 COLUMN_DESC,
 COLUMN_INSTALL,
 COLUMN_DETAILS,
 COLUMN_TOOLTIP,
 COLUMN_SCORE) = range(6)

DAEMON_IDLE_TIMEOUT = 3 * 60
DAEMON_IDLE_CHECK_INTERVAL = 30

# Required to get translated descriptions
try:
    locale.setlocale(locale.LC_ALL, "")
except locale.Error:
    log.debug("Failed to unset LC_ALL")

def track_usage(func):
    """Decorator to keep track of running methods and to update the time
    stamp of the last action.
    """
    @functools.wraps(func)
    def _track_usage(*args, **kwargs):
        def _release_track(ret, si):
            si._tracks -= 1
            si._last_timestamp = time.time()
            log.debug("Updating last_timestamp")
            return ret
        si = args[0]
        si._tracks += 1
        si._last_timestamp = time.time()
        log.debug("Updating last_timestamp")
        deferred = defer(func, *args, **kwargs)
        deferred.add_callbacks(_release_track, _release_track,
                               callback_args=[si],
                               errback_args=[si])
        return deferred
    return _track_usage


class GStreamerStructure(object):

    """Abstraction class of GStramer structure."""

    def __init__(self, name="", version="", kind="", record="", caps="",
                 element=""):
        self.name = name
        self.version = version
        self.kind = kind
        self.record = record
        self.caps = caps
        self.element = element
        self.satisfied = False
        self.best_provider = None
        self.best_score = -1


class GtkOpProgress(apt.progress.base.OpProgress):

    """A simple helper that keeps the GUI alive."""

    def __init__(self, progress=None):
        apt.progress.base.OpProgress.__init__(self)
        self.progress_dialog = progress

    def update(self, percent=None):
        while Gtk.events_pending():
            Gtk.main_iteration()
        if self.progress_dialog:
            self.progress_dialog.progress.pulse()


class ErrorDialog(Gtk.MessageDialog):

    """Allows to show an error message to the user."""

    def __init__(self, title, message, parent=None):
        GObject.GObject.__init__(self, message_type=Gtk.MessageType.ERROR,
                                   buttons=Gtk.ButtonsType.CLOSE)
        if parent:
            self.realize()
            self.set_transient_for(parent)
        self.set_markup("<b><big>%s</big></b>\n\n%s" % (title, message))


class ProgressDialog(Gtk.Dialog):

    """Allows to show the progress of an ongoing action to the user."""

    def __init__(self, title, message, parent=None):
        Gtk.Dialog.__init__(self)
        self.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        if parent:
            self.realize()
            self.set_transient_for(parent)
        self.set_title(title)
        self.set_resizable(False)
        self.set_border_width(12)
        self.vbox.set_spacing(24)
        self.label = Gtk.Label()
        self.label.set_markup("<b><big>%s</big></b>\n\n%s" % (title, message))
        self.label.set_line_wrap(True)
        self.vbox.add(self.label)
        self.progress = Gtk.ProgressBar()
        self.progress.set_pulse_step(0.01)
        self.vbox.add(self.progress)
        self.cancelled = False
        self.connect("response", self._on_response)

    def _on_response(self, dialog, response):
        if response == Gtk.ResponseType.CANCEL:
            self.cancelled = True


class ConfirmInstallDialog(Gtk.Dialog):

    """Allow to confirm an installation."""

    def __init__(self, title, message, pkgs=[], parent=None, details=None,
                 package_type=None, selectable=False, action=None):
        Gtk.Dialog.__init__(self)
        self.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        if parent:
            self.realize()
            self.set_transient_for(parent)
        self.set_title(title)
        self.set_resizable(True)
        self.set_border_width(12)
        self.vbox.set_spacing(12)
        self.icon = Gtk.Image.new_from_stock(Gtk.STOCK_DIALOG_QUESTION,
                                             Gtk.IconSize.DIALOG)
        self.icon.set_alignment(0 ,0)
        hbox_base = Gtk.HBox()
        hbox_base.set_spacing(24)
        vbox_left = Gtk.VBox()
        vbox_left.set_spacing(12)
        hbox_base.pack_start(self.icon, False, True, 0)
        hbox_base.pack_start(vbox_left, True, True, 0)
        self.label = Gtk.Label()
        self.label.set_alignment(0, 0)
        self.label.set_markup("<b><big>%s</big></b>\n\n%s" % (title, message))
        self.label.set_line_wrap(True)
        vbox_left.pack_start(self.label, False, True, 0)
        self.cancelled = False
        self.vbox.pack_start(hbox_base, True, True, 0)
        if not action:
            action = _("_Install")
        self.install_button = self.add_button(action, Gtk.ResponseType.OK)
        self.set_default_response(Gtk.ResponseType.OK)
        # Show a list of the plugin packages
        self.pkg_store = Gtk.ListStore(GObject.TYPE_STRING,
                                       GObject.TYPE_STRING,
                                       GObject.TYPE_BOOLEAN,
                                       GObject.TYPE_STRING,
                                       GObject.TYPE_STRING,
                                       GObject.TYPE_INT)
        self.pkg_store.set_sort_column_id(COLUMN_SCORE, Gtk.SortType.DESCENDING)
        self.pkg_view = Gtk.TreeView(self.pkg_store)
        self.pkg_view.set_rules_hint(True)
        self.pkg_view.props.has_tooltip = True
        self.pkg_view.connect("query-tooltip", self._on_query_tooltip)
        if selectable:
            toggle_install = Gtk.CellRendererToggle()
            toggle_install.connect("toggled", self._on_toggled_install)
            column_install = Gtk.TreeViewColumn(_("Install"), toggle_install,
                                                active=COLUMN_INSTALL)
            self.pkg_view.append_column(column_install)
        if not package_type:
            package_type = _("Package")
        column_desc = Gtk.TreeViewColumn(package_type)
        renderer_warn = Gtk.CellRendererPixbuf()
        renderer_warn.props.stock_size = Gtk.IconSize.MENU
        column_desc.pack_start(renderer_warn, False)
        column_desc.set_cell_data_func(renderer_warn, self._render_warning)
        renderer_desc = Gtk.CellRendererText()
        renderer_desc.props.ellipsize = Pango.EllipsizeMode.END
        column_desc.pack_start(renderer_desc, True)
        column_desc.add_attribute(renderer_desc, "markup", COLUMN_DESC)
        column_desc.props.expand = True
        column_desc.props.resizable = True
        column_desc.props.min_width = 50
        self.pkg_view.append_column(column_desc)
        if details:
            renderer_details = Gtk.CellRendererText()
            renderer_details.props.ellipsize = Pango.EllipsizeMode.END
            column_details = Gtk.TreeViewColumn(details,
                                                renderer_details)
            column_details.add_attribute(renderer_details, "markup",
                                         COLUMN_DETAILS)
            column_details.props.resizable = True
            column_details.props.min_width = 50
            self.pkg_view.append_column(column_details)
        if not (selectable or details):
            self.pkg_view.props.headers_visible = False
        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.NEVER)
        self.scrolled_window.set_shadow_type(Gtk.ShadowType.IN)
        self.scrolled_window.add(self.pkg_view)
        vbox_left.pack_start(self.scrolled_window, True, True, 0)
        self.install_button.props.sensitive = False
        for pkg in pkgs:
            self.add_confirm_package(pkg)

    def add_confirm(self, name, summary, active=True, details="", score=0,
                    restricted=False):
        """Add an entry to the confirmation dialog.

        Keyword arguments:
        name -- name of the package or file
        summary -- short description of the package
        active -- if the package should be selected by default
        details -- additional information about the package
        score -- the ranking of the package which should be used for ordering
        restricted -- if the use or redistribution is restriceted
        """
        if restricted:
            #TRANSLATORS: %s is the name of a piece of software
            tooltip = _("The use of %s may be restricted in some "
                        "countries. You must verify that one of the following "
                        "is true:\n"
                        "- These restrictions do not apply in your country "
                        "of legal residence\n"
                        "- You have permission to use this software (for "
                        "example, a patent license)\n"
                        "- You are using this software for research "
                        "purposes only") % name
            # Set the dialog default to cancel if a restricted packages is
            # selected for installation
            if active:
                self.set_default_response(Gtk.ResponseType.CANCEL)
        else:
            tooltip = ""
        desc = utils.get_package_desc(name, summary)
        self.pkg_store.append((name, desc, active, details, tooltip, score))
        if active:
            self.install_button.props.sensitive = True

    def add_confirm_package(self, pkg, active=True, details="", score=0):
        """Show an apt.package.Package instance in the confirmation dialog.

        Keyword arguments:
        pkg -- the apt.package.Package instance
        active -- if the package should be selected by default
        details -- additional information about the package
        score -- the ranking of the package which should be used for ordering
        """
        self.add_confirm(pkg.name, pkg.candidate.summary, active, details,
                         score, _is_package_restricted(pkg))

    def get_selected_pkgs(self):
        """Return a list of the package names which are selected."""
        return [pkg \
                for pkg, _desc, active, _details, _tooltip, _score \
                in self.pkg_store \
                if active]

    def _on_query_tooltip(self, treeview, x, y, keyboard_tip, tooltip):
        """Handle tooltips for restrcited packages."""
        try:
            result, out_x, out_y, model, path, iter = treeview.get_tooltip_context(x, y, keyboard_tip)
            if not result:
                return False
        except TypeError:
            return False

        text = model[path][COLUMN_TOOLTIP]
        if not text:
            return False
        tooltip.set_icon_from_icon_name(Gtk.STOCK_DIALOG_WARNING,
                                        Gtk.IconSize.DIALOG)
        tooltip.set_markup(text)
        treeview.set_tooltip_row(tooltip, path)
        return True

    def _on_toggled_install(self, toggle, path):
        """Handle an activated package."""
        cur = toggle.get_active()
        self.pkg_store[path][COLUMN_INSTALL] = not cur
        for row in self.pkg_store:
            if row[COLUMN_INSTALL]:
                self.install_button.props.sensitive = True
                return
        self.install_button.props.sensitive = False

    def _render_warning(self, cell, renderer, model, iter, data):
        """Show a warning icon for restricted packages."""
        if model.get_value(iter, COLUMN_TOOLTIP):
            renderer.props.stock_id = Gtk.STOCK_DIALOG_WARNING
        else:
            renderer.props.stock_id = None

    def run(self):
        """Run the dialog."""
        if len(self.pkg_store) > 4:
            self.scrolled_window.set_policy(Gtk.PolicyType.NEVER,
                                            Gtk.PolicyType.AUTOMATIC)
            self.pkg_view.set_size_request(-1, 240)
        self.show_all()
        res = Gtk.Dialog.run(self)
        self.hide()
        self.destroy()
        return res


class SessionInstaller(dbus.service.Object):

    """Provides the PackageKit session API."""

    def __init__(self, bus=None):
        log.info("Starting service")
        self.loop = GObject.MainLoop()
        if not bus:
            bus = dbus.SessionBus()
        self.bus = bus
        bus_name = dbus.service.BusName(PACKAGEKIT_DBUS_SERVICE, bus)
        dbus.service.Object.__init__(self, bus_name, PACKAGEKIT_DBUS_PATH)
        self._cache = None
        self.backend = Backend()
        GObject.timeout_add_seconds(DAEMON_IDLE_CHECK_INTERVAL,
                                    self._check_for_inactivity)
        self._tracks = 0
        self._last_timestamp = time.time()

    def _check_for_inactivity(self):
        """Quit after a period of inactivity."""
        idle_time = time.time() - self._last_timestamp
        log.debug("Checking for inactivity (%is)", idle_time)
        if not self._tracks and \
           not GObject.main_context_default().pending() and \
           idle_time > DAEMON_IDLE_TIMEOUT:
            self.loop.quit()
            log.info("Shutting down because of inactivity")
        return True

    def run(self):
        """Start listening for requests."""
        self.loop.run()

    def _init_cache(self, progress=None):
        """Helper to set up the package cache."""
        if not self._cache:
            self._cache = apt.Cache(GtkOpProgress(progress))

    @inline_callbacks
    def _get_sender_name(self, sender):
        """Try to resolve the name of the calling application."""
        pid = yield get_pid_from_dbus_name(sender, self.bus)
        try:
            exe = utils.get_process_exe(pid)
        except:
            return_value(None)
        # Try to get the name of an interpreted script
        if re.match("(/usr/bin/python([0-9]\.[0-9])?)|(/usr/bin/perl)", exe):
            try:
                exe = utils.get_process_cmdline(pid)[1]
            except (IndexError, OSError):
                pass
        # Special case for the GStreamer codec installation via the helper
        # gnome-packagekit returns the name of parent window in this case,
        # But this could be misleading:
        # return_value(parent.property_get("WM_NAME")[2])
        # So we try to identify the calling application
        if exe in ["/usr/libexec/pk-gstreamer-install",
                   "/usr/lib/pk-gstreamer-install",
                   "/usr/bin/gst-install",
                   "/usr/bin/gstreamer-codec-install"]:
            try:
                parent_pid = utils.get_process_ppid(pid)
                exe = utils.get_process_exe(parent_pid)
            except OSError:
                return_value(None)
        # Return the application name in the case of an installed application
        for app in Gio.app_info_get_all():
            if (app.get_executable() == exe or
                app.get_executable() == os.path.basename(exe)):
                return_value(app.get_name())
        return_value(os.path.basename(exe))

    def _parse_interaction(self, interaction):
        mode = 0
        interact_list = interaction.split(",")
        if "always" in interact_list:
            mode = INTERACT_ALWAYS
        elif "never" in interact_list:
            mode = INTERACT_NEVER
        if "show-confirm-progress" in interact_list:
            mode &= INTERACT_CONFIRM_PROGRESS
        elif "show-confirm-deps" in interact_list:
            mode &= INTERACT_CONFIRM_DEPS
        elif "show-confirm-install" in interact_list:
            mode &= INTERACT_CONFIRM_INSTALL
        elif "show-progress" in interact_list:
            mode &= INTERACT_PROGRESS
        elif "show-finished" in interact_list:
            mode &= INTERACT_FINISHED
        elif "show-warning" in interact_list:
            mode &= INTERACT_WARNING
        elif "hide-confirm-progress" in interact_list:
            mode |= INTERACT_CONFIRM_PROGRESS
        elif "hide-confirm-deps" in interact_list:
            mode |= INTERACT_CONFIRM_DEPS
        elif "hide-confirm-install" in interact_list:
            mode |= INTERACT_CONFIRM_INSTALL
        elif "hide-progress" in interact_list:
            mode |= INTERACT_PROGRESS
        elif "hide-finished" in interact_list:
            mode |= INTERACT_FINISHED
        elif "hide-warning" in interact_list:
            mode |= INTERACT_WARNING
        return mode

    @dbus_deferred_method(PACKAGEKIT_QUERY_DBUS_INTERFACE,
                          in_signature="ss", out_signature="b",
                          utf8_strings=True)
    def IsInstalled(self, package_name, interaction):
        """Return True if the given package is installed.

        Keyword arguments:
        package-name -- the name of the package, e.g. xterm
        interaction -- the interaction mode, e.g. timeout=10
        """
        log.info("IsInstalled() was called: %s, %s", package_name, interaction)
        return self._is_installed(package_name, interaction)

    @track_usage
    def _is_installed(self, package_name, interaction):
        self._init_cache()
        try:
            return self._cache[package_name].is_installed
        except KeyError:
            raise errors.QueryNoPackagesFound

    @dbus_deferred_method(PACKAGEKIT_QUERY_DBUS_INTERFACE,
                          in_signature="ss", out_signature="bs",
                          utf8_strings=True)
    def SearchFile(self, file_name, interaction):
        """Return the installation state and name of the package which
        contains the given file.

        Keyword arguments:
        file_name -- the to be searched file name
        interaction -- the interaction mode, e.g. timeout=10
        """
        log.info("SearchFile() was called: %s, %s", file_name, interaction)
        return self._search_file(file_name, interaction)

    @track_usage
    def _search_file(self, file_name, interaction):
        self._init_cache()
        # Search for installed files
        if file_name.startswith("/"):
            pattern = "^%s$" % file_name.replace("/", "\/")
        else:
            pattern = ".*\/%s$" % file_name
        re_file = re.compile(pattern)
        for pkg in self._cache:
            # FIXME: Fix python-apt
            try:
                for installed_file in pkg.installed_files:
                    if re_file.match(installed_file):
                        #FIXME: What about a file in multiple conflicting
                        # packages?
                        return pkg.is_installed, pkg.name
            except:
                pass
        # Optionally make use of apt-file's Contents cache to search for not
        # installed files. But still search for installed files additionally
        # to make sure that we provide up-to-date results
        if os.path.exists("/usr/bin/apt-file"):
            #FIXME: Make use of rapt-file on Debian if the network is available
            #FIXME: Show a warning to the user if the apt-file cache is several
            #       weeks old
            log.debug("Using apt-file")
            if file_name.startswith("/"):
                pattern = "^%s$" % file_name[1:].replace("/", "\/")
            else:
                pattern = "\/%s$" % file_name
            cmd = ["/usr/bin/apt-file", "--regexp", "--non-interactive",
                   "--package-only", "find", pattern]
            log.debug("Calling: %s" % cmd)
            apt_file = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)
            stdout, stderr = apt_file.communicate()
            if apt_file.returncode == 0:
                #FIXME: Actually we should check if the file is part of the
                #       candidate, e.g. if unstable and experimental are
                #       enabled and a file would only be part of the
                #       experimental version
                #FIXME: Handle multiple packages
                for pkg_name in stdout.split():
                    try:
                        pkg = self._cache[pkg_name]
                    except:
                        continue
                    return pkg.isInstalled, pkg.name
            else:
                raise errors.QueryInternatlError("apt-file call failed")
            return False, ""

    @dbus_deferred_method(PACKAGEKIT_MODIFY_DBUS_INTERFACE,
                          in_signature="uass", out_signature="",
                          sender_keyword="sender",
                          utf8_strings=True)
    def InstallPackageFiles(self, xid, files, interaction, sender):
        """Install local package files.

        Keyword arguments:
        xid -- the window id of the requesting application
        files -- the list of package file paths
        interaction -- the interaction mode: which ui elements should be
                       shown e.g. hide-finished or hide-confirm-search
        """
        log.info("InstallPackageFiles was called: %s, %s, %s", xid, files,
                 interaction)
        return self._install_package_files(xid, files, interaction, sender)

    @track_usage
    @inline_callbacks
    def _install_package_files(self, xid, files, interaction, sender):
        parent = None # should get from XID, but removed from Gdk 3
        header = ""
        if len(files) != 1:
            header = _("Failed to install multiple package files")
            message = _("Installing more than one package file at the same "
                        "time isn't supported. Please install one after the "
                        "other.")
        elif not files[0][0] == "/":
            header = _("Relative path to package file")
            message = _("You have to specify the absolute path to the "
                        "package file.")
        elif not files[0].endswith(".deb"):
            header = _("Unsupported package format")
            message = _("Only Debian packages are supported (*.deb)")
        try:
            debfile = apt.debfile.DebPackage(files[0])
            desc = debfile["Description"].split("\n", 1)[0]
        except:
            header = _("Unsupported package format")
            message = _("Only Debian packages are supported (*.deb)")
        if header:
            dia = ErrorDialog(header, message)
            dia.run()
            dia.hide()
            raise errors.ModifyFailed("%s - %s" % (header, message))
        title = gettext.ngettext("Install package file?",
                                 "Install package files?",
                                 len(files))
        sender_name = yield self._get_sender_name(sender)
        if sender_name:
            message = gettext.ngettext("%s requests to install the following "
                                       "package file.",
                                       "%s requests to install the following "
                                       "package files.",
                                       len(files)) % sender_name
            message += "\n\n"
        else:
            message = ""
        message += _("Software from foreign sources could be malicious, "
                     "could contain security risks and or even break your "
                     "system."
                     "Install packages from your distribution's "
                     "repositories as far as possible.")
        confirm = ConfirmInstallDialog(title, message, parent=parent)
        confirm.add_confirm(files[0], desc)
        if confirm.run() == Gtk.ResponseType.CANCEL:
            raise errors.ModifyCancelled
        yield self.backend.install_package_files(xid,
                                                 confirm.get_selected_pkgs(),
                                                 interaction)

    @dbus_deferred_method(PACKAGEKIT_MODIFY_DBUS_INTERFACE,
                          in_signature="uass", out_signature="",
                          sender_keyword="sender",
                          utf8_strings=True)
    def InstallProvideFiles(self, xid, files, interaction, sender):
        """Install packages which provide the given files.

        Keyword arguments:
        xid -- the window id of the requesting application
        files -- the list of package file paths
        interaction -- the interaction mode: which ui elements should be
                       shown e.g. hide-finished or hide-confirm-search
        """
        log.info("InstallProvideFiles() was called: %s, %s, %s", xid, files,
                 interaction)
        return self._install_provide_files(xid, files, interaction, sender)

    @track_usage
    @inline_callbacks
    def _install_provide_files(self, xid, files, interaction, sender):
        #FIXME: Reuse apt-file from the search_file method
        try:
            from CommandNotFound import CommandNotFound
        except ImportError:
            log.warning("command-not-found not supported")
        else:
            cnf = CommandNotFound("/usr/share/command-not-found")
            to_install = list()
            for executable in [os.path.basename(f) for f in files]:
                list_of_packages_and_components =  cnf.getPackages(executable)
                if list_of_packages_and_components:
                    (package, component) = list_of_packages_and_components[0]
                    to_install.append(package)
            if to_install:
                yield self._install_package_names(xid, to_install, interaction,
                                                  sender)
                raise StopIteration
            # FIXME: show a message here that the binaries were not
            #        found instead of falling through to the misleading
            #        other error message

        # FIXME: use a different error message
        header = _("Installing packages by files isn't supported")
        message = _("This method hasn't yet been implemented.")
        #FIXME: should provide some information about how to find apps
        dia = ErrorDialog(header, message)
        dia.run()
        dia.hide()
        #raise errors.ModifyInternalError(message)

    @dbus_deferred_method(PACKAGEKIT_MODIFY_DBUS_INTERFACE,
                          in_signature="uass", out_signature="",
                          sender_keyword="sender",
                          utf8_strings=True)
    def InstallCatalogs(self, xid, files, interaction, sender):
        """Install packages which provide the given files.

        Keyword arguments:
        xid -- the window id of the requesting application
        files -- the list of catalog file paths
        interaction -- the interaction mode: which ui elements should be
                       shown e.g. hide-finished or hide-confirm-search
        """
        log.info("InstallCatalogs() was called: %s, %s, %s", xid, files,
                 interaction)
        return self._install_catalogs(xid, files, interaction, sender)

    @track_usage
    @inline_callbacks
    def _install_catalogs(self, xid, files, interaction, sender):
        parent = None # should get from XID, but removed from Gdk 3
        self._init_cache()
        arch = os.popen("/usr/bin/dpkg --print-architecture").read().strip()
        distro, code, release = os.popen("/usr/bin/lsb_release "
                                         "--id --code --release "
                                         "--short").read().split()
        regex = "^(?P<action>[a-z]+)(\(%s(;((%s)|(%s))(;%s)?)?\))?$" % \
                (distro, code, release, arch)
        re_action = re.compile(regex, flags=re.IGNORECASE)
        pkgs = set()
        missing = set()
        for catalog_file in files:
            if not os.path.exists(catalog_file):
                header = _("Catalog could not be read")
                #TRANSLATORS: %s is a file path
                message = _("The catalog file '%s' doesn't "
                            "exist.") % catalog_file
                self._show_error(header, message)
                raise errors.ModifyFailed(message)
            catalog = ConfigParser()
            try:
                catalog.read(catalog_file)
            except:
                header = _("Catalog could not be read")
                #TRANSLATORS: %s is a file path
                message = _("The catalog file '%s' could not be opened  "
                            "and read.") % catalog_file
                self._show_error(header, message)
                raise errors.ModifyFailed(message)
            if not catalog.sections() == ["PackageKit Catalog"]:
                header = _("Catalog could not be read")
                #TRANSLATORS: %s is a file path
                message = _("The file '%s' isn't a valid software catalog. "
                            "Please redownload or contact the "
                            "provider.") % catalog_file
                self._show_error(header, message)
                raise errors.ModifyFailed(message)
            for key, value in catalog.items("PackageKit Catalog"):
                match = re_action.match(key)
                if match:
                    if match.group("action") != "installpackages":
                        header = _("Catalog is not supported")
                        message = _("The method '%s' which is used to specify "
                                    "packages isn't supported.\n"
                                    "Please contact the provider of the "
                                    "catalog about this "
                                    "issue.") % match.group("action")
                        self._show_error(header, message)
                        raise errors.ModifyFailed(message)
                    for pkg_name in value.split(";"):
                        if pkg_name in self._cache:
                            pkg = self._cache[pkg_name]
                            if not pkg.is_installed and not pkg.candidate:
                                missing.add(pkg_name)
                            else:
                                pkgs.add(self._cache[pkg_name])
                        else:
                            missing.add(pkg_name)
                else:
                    log.debug("Ignoring catalog instruction: %s" % key)
        # Error out if packages are not available
        if missing:
            header = gettext.ngettext("A required package is not installable",
                                      "Required packages are not installable",
                                      len(missing))
            pkgs = " ".join(missing)
            #TRANSLATORS: %s is the name of the missing packages
            msg = gettext.ngettext("The catalog requires the installation of "
                                   "the package %s which is not available.",
                                   "The catalog requires the installation of "
                                   "the following packages which are not "
                                   "available: %s", len(missing)) % pkgs
            self._show_error(header, msg)
            raise errors.ModifyNoPackagesFound(msg)
        parent = None # should get from XID, but removed from Gdk 3
        # Create nice messages
        sender_name = yield self._get_sender_name(sender)
        title = gettext.ngettext("Install the following software package?",
                                 "Install the following software packages?",
                                 len(pkgs))
        if sender_name:
            #TRANSLATORS: %s is the name of the application which requested
            #             the installation
            message = gettext.ngettext("%s requires the installation of an "
                                       "additional software package.",
                                       "%s requires the installation of "
                                       "additional software packages.",
                                       len(pkgs)) % sender_name
        else:
            #TRANSLATORS: %s is an absolute file path, e.g. /usr/bin/xterm
            message = gettext.ngettext("The package catalog %s requests to "
                                       "install the following software.",
            #TRANSLATORS: %s is a list of absoulte file paths
                                       "The following catalogs request to "
                                       "install software: %s",
            #TRANSLATORS: %s is an absolute file path, e.g. /usr/bin/xterm
                                       len(files)) % " ".join("'%s'")
        confirm = ConfirmInstallDialog(title, message, pkgs, parent)
        res = confirm.run()
        if res == Gtk.ResponseType.OK:
            yield self.backend.install_packages(xid,
                                                confirm.get_selected_pkgs(),
                                                interaction)
        else:
            raise errors.ModifyCancelled

    @dbus_deferred_method(PACKAGEKIT_MODIFY_DBUS_INTERFACE,
                          in_signature="uass", out_signature="",
                          sender_keyword="sender",
                          utf8_strings=True)
    def InstallPackageNames(self, xid, packages, interaction, sender):
        """Install packages from a preconfigured software source.

        Keyword arguments:
        xid -- the window id of the requesting application
        packages -- the list of package names
        interaction -- the interaction mode: which ui elements should be
                       shown e.g. hide-finished or hide-confirm-search
        """
        log.info("InstallPackageNames() was called: %s, %s, %s", xid, packages,
                 interaction)
        return self._install_package_names(xid, packages, interaction, sender)

    @track_usage
    @inline_callbacks
    def _install_package_names(self, xid, packages, interaction, sender):
        parent = None # should get from XID, but removed from Gdk 3
        title = gettext.ngettext("Install additional software package?",
                                 "Install additional software packages?",
                                 len(packages))
        sender_name = yield self._get_sender_name(sender)
        if sender_name:
            message = gettext.ngettext("%s requests to install the following "
                                       "software package to provide additional "
                                       "features.",
                                       "%s requests to install the following "
                                       "software packages to provide "
                                       "additional features.",
                                       len(packages)) % sender_name
        else:
            message = gettext.ngettext("The following software package is "
                                       "required to provide additional "
                                       "features.",
                                       "The following software packages are "
                                       "required to provide additional "
                                       "features.",
                                       len(packages))
        self._init_cache()
        confirm = ConfirmInstallDialog(title, message, parent=parent)
        failed_packages = []
        for pkg_name in packages:
            try:
                pkg = self._cache[pkg_name]
            except KeyError:
                failed_packages.append(pkg_name)
                continue
            if not pkg.candidate:
                failed_packages.append(pkg_name)
                continue
            if not pkg.is_installed:
                confirm.add_confirm_package(pkg)

        if failed_packages:
            header = gettext.ngettext("Could not find requested package",
                                      "Could not find requested packages",
                                      len(failed_packages))
            if sender_name:
                message = gettext.ngettext("%s requests to install the "
                                           "following software package to "
                                           "provide "
                                           "additional features:",
                                           "%s requests to install the "
                                           "following "
                                           "software packages to provide "
                                           "additional features:",
                                           len(packages)) % sender_name
            else:
                message = gettext.ngettext("The following software package "
                                           "is required to provide "
                                           "additional features but cannot "
                                           "be installed:",
                                           "The following software "
                                           "packages are required to "
                                           "provide "
                                           "additional features but cannot "
                                           "be installed:",
                                           len(failed_packages))
            message += self._get_bullet_list(failed_packages)
            self._show_error(header, message)
            raise errors.ModifyNoPackagesFound(header)
        # If all packages are already installed we return silently
        if len(confirm.pkg_store) > 0:
            if confirm.run() == Gtk.ResponseType.CANCEL:
                raise errors.ModifyCancelled
            yield self.backend.install_packages(xid,
                                                confirm.get_selected_pkgs(),
                                                interaction)

    @dbus_deferred_method(PACKAGEKIT_MODIFY_DBUS_INTERFACE,
                          in_signature="uass", out_signature="",
                          sender_keyword="sender",
                          utf8_strings=True)
    def InstallMimeTypes(self, xid, mime_types, interaction, sender):
        """Install mime type handler from a preconfigured software source.

        Keyword arguments:
        xid -- the window id of the requesting application
        mime_types -- list of mime types whose handlers should be installed
        interaction -- the interaction mode: which ui elements should be
                       shown e.g. hide-finished or hide-confirm-search
        """
        log.info("InstallMimeTypes() was called: %s, %s, %s", xid, mime_types,
                 interaction)
        return self._install_mime_types(xid, mime_types, interaction, sender)

    @track_usage
    @inline_callbacks
    def _install_mime_types(self, xid, mime_types_list, interaction, sender):
        parent = None # should get from XID, but removed from Gdk 3
        if not os.path.exists(utils.APP_INSTALL_DATA):
            #FIXME: should provide some information about how to find apps
            header = _("Installing mime type handlers isn't supported")
            message = _("To search and install software which can open "
                        "certain file types you have to install "
                        "app-install-data.")
            dia = ErrorDialog(header, message)
            dia.run()
            dia.hide()
            raise errors.ModifyInternalError(message)
        sender_name = yield self._get_sender_name(sender)
        title = _("Searching for suitable software to open files")
        mime_types = set(mime_types_list)
        mime_names = [Gio.content_type_get_description(mt) for mt in mime_types]
        if sender_name:
            #TRANSLATORS: %s is an application
            message = gettext.ngettext("%s requires to install software to "
                                       "open files of the following file type:",
                                       "%s requires to install software to "
                                       "open files of the following file "
                                       "types:",
                                       len(mime_types)) % sender_name
        else:
            message = gettext.ngettext("Software to open files of the "
                                       "following file type is required "
                                       "but is not installed:",
                                       "Software to open files of the "
                                       "following file types is required "
                                       "but is not installed:",
                                       len(mime_types))
        mime_types_desc = [Gio.content_type_get_description(mime_type) \
                           for mime_type in mime_types]
        message += self._get_bullet_list(mime_types_desc)
        progress = ProgressDialog(title, message, parent)
        progress.show_all()
        while Gtk.events_pending():
            Gtk.main_iteration()
        # Search the app-install-data desktop files for mime type handlers
        pkgs = []
        partial_providers = False
        self._init_cache(progress)
        package_map = {}
        unsatisfied = mime_types.copy()
        mixed = False
        for count, path in enumerate(os.listdir(utils.APP_INSTALL_DATA)):
            if path[0] == "." or not path.endswith(".desktop"):
                continue
            if not count % 20:
                while Gtk.events_pending():
                    Gtk.main_iteration()
                progress.progress.pulse()
                if progress.cancelled:
                    progress.hide()
                    progress.destroy()
                    raise errors.ModifyCancelled
            try:
                desktop_entry = DesktopEntry(os.path.join(utils.APP_INSTALL_DATA,
                                                      path))
            except ParsingError:
                continue
            pkg_name = desktop_entry.get("X-AppInstall-Package")
            try:
                if self._cache[pkg_name].is_installed:
                    continue
            except KeyError:
                continue
            supported_mime_types = set(desktop_entry.getMimeTypes())
            for mime_type in supported_mime_types:
                if not mime_type in mime_types:
                    continue
                package_map.setdefault(pkg_name, [[], set(), 0])
                #FIXME: Don't add desktop entries twice
                package_map[pkg_name][0].append(desktop_entry)
                desc = Gio.content_type_get_description(mime_type)
                package_map[pkg_name][1].add(desc)
                popcon = desktop_entry.get("X-AppInstall-Popcon",
                                           type="integer")
                if package_map[pkg_name][2] < popcon:
                    package_map[pkg_name][2] = popcon
                unsatisfied.discard(mime_type)
                if not mixed and \
                   not supported_mime_types.issuperset(mime_types):
                    mixed = True
        progress.hide()
        progress.destroy()
        if mixed or unsatisfied:
            details = _("Supported file types")
        else:
            details = None
        title = _("Install software to open files?")
        if unsatisfied:
            unsatisfied_desc = [Gio.content_type_get_description(mime_type) \
                                for mime_type in unsatisfied]
            unsatisfied_str = self._get_bullet_list(unsatisfied_desc)
            message += "\n\n"
            #TRANSLATORS: %s is either a single file type or a bullet list of
            #             file types
            message += gettext.ngettext("%s is not supported.",
                                        "Unsupported file types: %s",
                                        len(unsatisfied)) % unsatisfied_str
        confirm = ConfirmInstallDialog(title, message, parent=parent,
                                       details=details,
                                       selectable=len(package_map) > 1,
                                       package_type=_("Application"))
        for pkg, (entries, provides, score) in package_map.iteritems():
            if len(provides) == len(mime_types):
                details = _("All")
            else:
                #TRANSLATORS: Separator for a list of plugins
                details = _(",\n").join(provides)
            confirm.add_confirm_package(self._cache[pkg], len(package_map) == 1,
                                        details, score)
        res = confirm.run()
        if res == Gtk.ResponseType.OK:
            yield self.backend.install_packages(xid,
                                                confirm.get_selected_pkgs(),
                                                interaction)
        else:
            raise errors.ModifyCancelled

    @dbus_deferred_method(PACKAGEKIT_MODIFY_DBUS_INTERFACE,
                          in_signature="uass", out_signature="",
                          utf8_strings=True)
    def InstallPrinterDrivers(self, xid, resources, interaction):
        """Install printer drivers from from a preconfigured software source.

        Keyword arguments:
        xid -- the window id of the requesting application
        resources -- a list of printer model descriptors in IEEE 1284
               Device ID format e.g. "MFG:Hewlett-Packard" "MDL:HP LaserJet6MP"
        interaction -- the interaction mode: which ui elements should be
               shown e.g. hide-finished or hide-confirm-search
        """
        log.info("InstallPrinterDrivers() was called: %s, %s, %s", xid,
                 resources, interaction)
        return self._install_printer_drivers(xid, resources, interaction)

    @track_usage
    def _install_printer_drivers(self, xid, resources, interaction):
	return
        header = _("Installing printer drivers on request isn't supported")
        message = _("Currently autodetection and installation of "
                    "missing printer drivers is not supported.")
        #FIXME: should provide some information about how to get printers
        dia = ErrorDialog(header, message)
        dia.run()
        dia.hide()
        raise errors.ModifyInternalError(message)

    @dbus_deferred_method(PACKAGEKIT_MODIFY_DBUS_INTERFACE,
                          in_signature="uass", out_signature="",
                          utf8_strings=True)
    def InstallFontconfigResources(self, xid, resources, interaction,):
        """Install fontconfig resources from from a
        preconfigured software source.

        Keyword arguments:
        xid -- the window id of the requesting application
        resources -- list of fontconfig resources (usually fonts)
        interaction -- the interaction mode: which ui elements should be
                       shown e.g. hide-finished or hide-confirm-search
        """
        log.info("InstallFontconfigResources() was called: %s, %s, %s", xid,
                 resources, interaction)
        return self._install_fontconfig_resources(xid, resources, interaction)

    @track_usage
    def _install_fontconfig_resources(self, xid, resources, interaction):
        header = _("Installing fonts on request isn't supported")
        message = _("Currently autodetection and installation of "
                    "missing fonts is not supported.")
        #FIXME: should provide some information about how to get fonts
        dia = ErrorDialog(header, message)
        dia.run()
        dia.hide()
        raise errors.ModifyInternalError(message)

    @dbus_deferred_method(PACKAGEKIT_MODIFY_DBUS_INTERFACE,
                          in_signature="uass", out_signature="",
                          sender_keyword="sender",
                          utf8_strings=True)
    def InstallGStreamerResources(self, xid, resources, interaction, sender):
        """Install GStreamer resources from from a preconfigured
        software source.

        Keyword arguments:
        xid -- the window id of the requesting application
        resources -- list of GStreamer structures, e.g.
                     "gstreamer0.10(decoder-video/x-wmv)(wmvversion=3)"
        interaction -- the interaction mode: which ui elements should be
                       shown e.g. hide-finished or hide-confirm-search
        """
        log.info("InstallGstreamerResources() was called: %s, %s, %s", xid,
                 resources, interaction)
        Gst.init(None)
        return self._install_gstreamer_resources(xid, resources, interaction,
                                                 sender)

    @track_usage
    @inline_callbacks
    def _install_gstreamer_resources(self, xid, resources, interaction, sender):
        def parse_gstreamer_structure(resource):
            # E.g. "MS Video|gstreamer0.10(decoder-video/x-wmv)(wmvversion=3)"
            match = re.match("^(?P<name>.*)\|gstreamer(?P<version>[0-9\.]+)"
                             "\((?P<kind>.+?)-(?P<structname>.+?)\)"
                             "(?P<fields>\(.+\))?$", resource)
            caps = None
            element = None
            if not match:
                title = _("Invalid search term")
                message = _("The following term doesn't describe a "
                           "GStreamer resource: %s") % resource
                self._show_error(title, message)
                raise errors.ModifyFailed(message)
            if match.group("kind") in ["encoder", "decoder"]:
                caps_str = "%s" % match.group("structname")
                if match.group("fields"):
                    for field in re.findall("\((.+?=(\(.+?\))?.+?)\)",
                                            match.group("fields")):
                        caps_str += ", %s" % field[0]
                # gst.Caps.__init__ cannot handle unicode instances
                caps = Gst.Caps.from_string(str(caps_str))
            else:
                element = match.group("structname")
            record = GSTREAMER_RECORD_MAP[match.group("kind")]
            return GStreamerStructure(match.group("name"),
                                      match.group("version"),
                                      match.group("kind"),
                                      record, caps, element)

        structures = [parse_gstreamer_structure(res) for res in resources]
        kinds = set([struct.kind for struct in structures])
        # Show a progress dialog
        parent = None # should get from XID, but removed from Gdk 3
        sender_name = yield self._get_sender_name(sender)
        title = _("Searching for multimedia plugins")
        # Get a nice dialog message
        if kinds.issubset(set(["encoder"])):
            if sender_name:
                #TRANSLATORS: %s is the application requesting the plugins
                message = gettext.ngettext("%s requires to install plugins to "
                                           "create media files of the "
                                           "following type:",
                                           "%s requires to install plugins to "
                                           "create files of the following "
                                           "types:",
                                           len(structures)) % sender_name
            else:
                message = gettext.ngettext("The plugin to create media files "
                                           "of the following type is not "
                                           "installed:",
                                           "The plugin to create media files "
                                           "of the following types is not "
                                           "installed:",
                                           len(structures))
        elif kinds.issubset(set(["decoder"])):
            if sender_name:
                #TRANSLATORS: %s is the application requesting the plugins
                message = gettext.ngettext("%s requires to install plugins to "
                                           "play media files of the "
                                           "following type:",
                                           "%s requires to install plugins to "
                                           "play files of the following "
                                           "types:",
                                           len(structures)) % sender_name
            else:
                message = gettext.ngettext("The plugin to play media files "
                                           "of the following type is not "
                                           "installed:",
                                           "The plugin to play media files "
                                           "of the following types is not "
                                           "installed:",
                                           len(structures))
        elif kinds.issubset(set(["encoder", "decoder"])):
            if sender_name:
                #TRANSLATORS: %s is the application requesting the plugins
                message = gettext.ngettext("%s requires to install plugins to "
                                           "create and play media files of the "
                                           "following type:",
                                           "%s requires to install plugins to "
                                           "create and play media files of the "
                                           "following types:",
                                           len(structures)) % sender_name
            else:
                message = gettext.ngettext("The plugins to create and play "
                                           "media files of the following type "
                                           "are not installed:",
                                           "The plugins to create and play "
                                           "media files of the following types "
                                           "are not installed:",
                                           len(structures))
        else:
            if sender_name:
                #TRANSLATORS: %s is the application requesting the plugins
                message = gettext.ngettext("%s requires to install plugins to "
                                           "support the following "
                                           "multimedia feature:",
                                           "%s requires to install plugins to "
                                           "support the following multimedia "
                                           "features:",
                                           len(structures)) % sender_name
            else:
                message = gettext.ngettext("Extra plugins to provide the "
                                           "following multimedia feature are "
                                           "not installed:",
                                           "Extra plugins to provide the "
                                           "following multimedia features are "
                                           "not installed:",
                                           len(structures))
        message += self._get_bullet_list([struct.name or struct.record \
                                         for struct in structures])
        progress = ProgressDialog(title, message, parent)
        progress.show_all()
        while Gtk.events_pending():
            Gtk.main_iteration()
        # Search the package cache for packages providing the plugins
        pkgs = []
        partial_providers = False
        self._init_cache(progress)

        # Get the architectures with an installed gstreamer library
        # Unfortunately the architecture isn't part of the request. So we
        # have to detect for which architectuers gstreamer has been installed
        # on the system, to avoid showing codecs for not used  but enabeled
        # architecures, see LP #899001
        architectures = apt_pkg.get_architectures()
        supported_archs = set()
        if len(architectures) > 1:
            for gst_version in set([struct.version for struct in structures]):
                for arch in architectures:
                    try:
                        pkg = self._cache["libgstreamer%s-0:%s" % (gst_version,
                                                                   arch)]
                    except KeyError:
                        continue
                    if pkg.is_installed:
                        supported_archs.add(arch)
        else:
            supported_archs = architectures

        for count, pkg in enumerate(self._cache):
            if not count % 100:
                while Gtk.events_pending():
                    Gtk.main_iteration()
                progress.progress.pulse()
                if progress.cancelled:
                    progress.hide()
                    progress.destroy()
                    raise errors.ModifyCancelled
            if (pkg.is_installed or
                not pkg.candidate or 
                not "Gstreamer-Version" in pkg.candidate.record or
                not pkg.candidate.architecture in supported_archs):
                continue
            # Check if the package could not be free in usage or distribution
            # Allow to prefer special packages
            try:
                pkg_name = pkg.name.split(":")[0]
                if pkg_name in GSTREAMER_010_SCORING.keys():
                    score = GSTREAMER_010_SCORING[pkg_name]
                elif pkg_name in GSTREAMER_10_SCORING.keys():
                    score = GSTREAMER_10_SCORING[pkg_name]
                else:
                    raise KeyError
            except KeyError:
                score = 0
            if _is_package_restricted(pkg):
                score -= 10
            provides = []
            for struct in structures:
                if pkg.candidate.record["Gstreamer-Version"].split(".")[0] != struct.version.split(".")[0]:
                    continue
                if struct.caps:
                    try:
                        pkg_caps = Gst.Caps.from_string(pkg.candidate.record[struct.record])
                    except KeyError:
                        continue
                    if pkg_caps.intersect(struct.caps).is_empty():
                        continue
                else:
                    try:
                        elements = pkg.candidate.record[struct.record]
                    except KeyError:
                        continue
                    if not struct.element in elements:
                        continue
                provides.append(struct.name)
                struct.satisfied = True
                if score > struct.best_score:
                    struct.best_provider = pkg.name.split(":")[0]
                    struct.best_score = score
            if provides:
                provides_all = len(structures) == len(provides)
                if not provides_all:
                    partial_providers = True
                pkgs.append((pkg, provides_all, provides, score))
        progress.hide()
        progress.destroy()
        # Error out if there isn't any package available
        if not pkgs:
            #FIXME: Add more info and possible solutions for the user
            dia = ErrorDialog(_("Required plugin could not be found"),
                              message)
            dia.run()
            dia.hide()
            raise errors.ModifyNoPackagesFound
        # Show a confirmation dialog
        title = gettext.ngettext("Install extra multimedia plugin?",
                                 "Install extra multimedia plugins?",
                                 len(pkgs))
        unsatisfied = [stru.name for stru in structures if not stru.satisfied]
        if unsatisfied:
            message += "\n\n"
            message += gettext.ngettext("The following plugin is not "
                                        "available:",
                                        "The following plugins are not "
                                        "available:",
                                        len(unsatisfied))
            message += " "
            #TRANSLATORS: list separator
            message += self._get_bullet_list(unsatisfied)

        # We only show the details if there are packages which would only
        # provide a subset of the requests
        if partial_providers:
            details = _("Provides")
        else:
            details = None
        best_providers = set([struct.best_provider for struct in structures])
        confirm = ConfirmInstallDialog(title, message, parent=parent,
                                       details=details,
                                       selectable=len(pkgs) > 1,
                                       package_type=_("Plugin Package"))
        for pkg, provides_all, provides, score in pkgs:
            if provides_all:
                details = _("All")
            else:
                #TRANSLATORS: Separator for a list of plugins
                details = _(",\n").join(provides)
            # Skip the architecture from the name
            install = pkg.name.split(":")[0] in best_providers
            confirm.add_confirm_package(pkg, install, details, score)
        res = confirm.run()
        if res == Gtk.ResponseType.OK:
            yield self.backend.install_packages(xid,
                                                confirm.get_selected_pkgs(),
                                                interaction)
        else:
            raise errors.ModifyCancelled

    @dbus_deferred_method(PACKAGEKIT_MODIFY_DBUS_INTERFACE,
                          in_signature="uass", out_signature="",
                          sender_keyword="sender",
                          utf8_strings=True)
    def RemovePackageByFiles(self, xid, files, interaction, sender):
        """Remove packages which provide the given files.

        Keyword arguments:
        xid -- the window id of the requesting application
        files -- the list of file paths
        interaction -- the interaction mode: which ui elements should be
                       shown e.g. hide-finished or hide-confirm-search
        """
        log.info("RemovePackageByFiles() was called: %s, %s, %s", xid, files,
                 interaction)
        return self._remove_package_by_files(xid, files, interaction, sender)

    @track_usage
    @inline_callbacks
    def _remove_package_by_files(self, xid, files, interaction, sender):
        parent = None # should get from XID, but removed from Gdk 3
        sender_name = yield self._get_sender_name(sender)
        if [filename for filename in files if not filename.startswith("/")]:
            raise errors.ModifyFailed("Only absolute file names")
        pkgs = []
        title = _("Searching software to be removed")
        if sender_name:
            message = gettext.ngettext("%s wants to remove the software "
                                       "which provides the following file:",
                                       "%s wants to remove the software which "
                                       "provides the following files:",
                                       len(files)) % sender_name
        else:
            message = gettext.ngettext("The software which provides the "
                                       "following file is requested to be "
                                       "removed:"
                                       "The software which provides the "
                                       "following files is requested to be "
                                       "removed:",
                                       len(files))
        message += self._get_bullet_list(files)
        progress = ProgressDialog(title, message, parent)
        progress.show_all()
        self._init_cache(progress)
        for pkg in self._cache:
            try:
                for installed_file in pkg.installed_files:
                    if installed_file in files:
                        pkgs.append(pkg)
            except:
                pass
        progress.hide()
        if not pkgs:
            self._show_error(_("Files are not installed"),
                             _("The files which should be removed are not "
                               "part of any installed software."))
            raise errors.ModifyNoPackagesFound
        title = gettext.ngettext("Remove software package?",
                                 "Remove software packages?", len(pkgs))
        if sender_name:
            #TRANSLATORS: %s is the name of an application
            message = gettext.ngettext("%s wants to remove the following "
                                       "software package from your computer.",
                                       "%s wants to remove the following "
                                       "software packages from your computer.",
                                       len(pkgs)) % sender_name
        else:
            message = gettext.ngettext("The following software package "
                                       "will be removed from your computer.",
                                       "The following software packages "
                                       "will be removed from your computer.",
                                       len(pkgs))
        confirm = ConfirmInstallDialog(title, message, parent=parent,
                                       selectable=len(pkgs) > 1, pkgs=pkgs,
                                       action=_("_Remove"))
        res = confirm.run()
        if res == Gtk.ResponseType.OK:
            yield self.backend.remove_packages(xid,
                                               confirm.get_selected_pkgs(),
                                               interaction)
        else:
            raise errors.ModifyCancelled

    def _show_error(self, header, message):
        """Show an error dialog."""
        dialog = ErrorDialog(header, message)
        dialog.run()
        dialog.hide()

    def _get_bullet_list(self, lst):
        """Return a string with a bullet list for the given list."""
        text = ""
        if len(lst) == 1:
            text += " "
            text += lst[0]
        else:
            for element in lst:
                text += "\n• %s" % element
        return text


def _is_package_restricted(pkg):
    """If a package is possibly restricted in use."""
    return (pkg.name.split(":")[0] in RESTRICTED_010_PACKAGES + RESTRICTED_10_PACKAGES \
            or pkg.candidate.origins[0].component in ("non-free",
                                                   "restricted",
                                                   "multiverse"))

def main():
    log.setLevel(logging.DEBUG)
    si = SessionInstaller()
    si.run()

if __name__ == "__main__":
    main()

# vim:ts=4:sw=4:et
