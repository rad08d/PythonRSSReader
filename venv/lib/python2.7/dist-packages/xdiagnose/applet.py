#!/usr/bin/python3
# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Copyright (C) 2010-2012 Bryce Harrington <bryce@canonical.com>
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import os
import sys
import stat
import subprocess
import shutil
from gi.repository import Gtk
from gi.repository.GdkPixbuf import Pixbuf
import re
import tempfile
import gettext
from gettext import gettext as _

from xdiagnose.config_update import (
    config_update,
    config_dict,
    safe_backup,
    )
from xdiagnose.errors_treeview import ErrorsTreeView

class XDiagnoseApplet(Gtk.Window):
    def __init__(self):
        self.__enable_debugging = None
        self.__enable_apport = None
        self.__disable_splash = None
        self.__disable_vesafb = None
        self.__disable_pat = None
        self.__disable_grub_graphics = None
        self.__grub_gfxpayload_linux = None
        self.__grub_config_filename = '/etc/default/grub'
        self.kparams = {}
        self.is_running = True

        if not os.path.exists(self.__grub_config_filename):
            print("Error: No %s present" %(self.__grub_config_filename))
            sys.exit(1)

        Gtk.Window.__init__(self)
        self.set_title(_("X Diagnostics Settings"))
        self.set_size_request(300,200)
        self.set_border_width(10)
        self.connect("delete-event", self.on_close)
        self.connect("destroy", self.on_close)

        vbox = Gtk.VBox()
        vbox.set_spacing(20)
        self.add(vbox)

        vbox.pack_start(self.build_toolbar(), True, True, 0)
        vbox.pack_start(self.build_settings_list(
            title=_("Debug"), settings=[
                {'text':_("Extra graphics _debug messages"),
                 'tip':_("Makes dmesg logs more verbose with details about 3d, plymouth, and monitor detection"),
                 'active':self.has_enable_debugging(),
                 'handler':self.handle_enable_debugging},
                {'text':_("Display boot messages"),
                 'tip':_("Removes splash and quiet from kernel options so you can see kernel details during boot"),
                 'active':self.has_disable_splash(),
                 'handler':self.handle_disable_splash},
                {'text':_("Enable automatic crash bug reporting"),
                 'tip':_("Turns on the Apport crash detection and bug reporting tool"),
                 'active':self.has_enable_apport(),
                 'handler':self.handle_enable_apport},
                ]), True, True, 0)
        vbox.pack_start(self.build_settings_list(
            title=_("Workarounds"), settings=[
                {'text':_("Disable bootloader _graphics"),
                 'tip':_("The grub bootloader has a graphics mode using the VESA framebuffer driver which can sometimes interfere with later loading of the proper video driver.  Checking this forces grub to use text mode only."),
                 'active':self.has_disable_grub_graphics(),
                 'handler':self.handle_disable_grub_graphics},
                {'text':_("Disable _VESA framebuffer driver"),
                 'tip':_("vesafb is loaded early during boot so the boot logo can display, but can cause issues when switching to a real graphics driver.  Checking this prevents vesafb from loading so these issues do not occur."),
                 'active':self.has_disable_vesafb(),
                 'handler':self.handle_disable_vesafb},
                {'text':_("Disable _PAT memory"),
                 'tip':_("This pagetable extension can interfere with the memory management of proprietary drivers under certain situations and cause lagging or failures to allocate video memory, so turning it off can prevent those problems."),
                 'active':self.has_disable_pat(),
                 'handler':self.handle_disable_pat},
                ]), True, True, 0)

        button_box = Gtk.HBox()
        button_box.set_spacing(20)
        vbox.add(button_box)

        apply_button = Gtk.Button("Apply")
        apply_button.connect('clicked', self.on_apply)
        button_box.add(apply_button)

        close_button = Gtk.Button("Close")
        close_button.connect('clicked', self.on_close)
        button_box.add(close_button)

        self.show_all()

        # Where is our data dir?
        datadir = None
        for d in [
            os.path.relpath(os.path.join(os.path.dirname(__file__), "../data")),
            "/usr/local/share/xdiagnose",
            "/usr/share/xdiagnose"]:
            if os.path.exists(d):
                datadir = d
                break

        # Icons
        icon_file = os.path.join(datadir, 'icons', 'microscope.svg')
        pixbuf = Pixbuf.new_from_file(icon_file)
        self.set_icon(pixbuf)

    def destroy(self, widget=None, event=None, data=None):
        self.is_running = False
        self.destroy()
        return False

    def build_toolbar(self):
        hbox = Gtk.HBox()
        hbox.set_spacing(10)

        b = Gtk.Button(_("View Errors"))
        b.connect('clicked', self.on_scan_errors)
        hbox.pack_start(b, False, False, 0)

        b = Gtk.Button(_("Report an Xorg Bug"))
        b.connect('clicked', self.on_report_bug_action)
        hbox.pack_start(b, False, False, 0)

        return hbox

    def build_settings_list(self, title, settings=None):
        frame = Gtk.Frame()
        frame.set_shadow_type(Gtk.ShadowType.NONE)

        label = Gtk.Label(label="<b>%s</b>" %(title))
        label.set_use_markup(True)
        frame.set_label_widget(label)

        alignment = Gtk.Alignment.new(0.5, 0.5, 1.0, 1.0)
        alignment.set_padding(5, 0, 12, 0)

        vbox = Gtk.VBox()
        for s in settings:
            checkbutton = Gtk.CheckButton(s['text'], use_underline=True)
            checkbutton.connect("toggled", s['handler'])
            if 'tip' in s and s['tip']:
                checkbutton.set_tooltip_text(s['tip'])
            if 'active' in s:
                if s['active']:
                    checkbutton.set_active(1)
                else:
                    checkbutton.set_active(0)
            if 'inconsistent' in s and s['inconsistent']:
                checkbutton.set_inconsistent(s['inconsistent'])
            vbox.pack_start(checkbutton, False, False, 0)

        alignment.add(vbox)
        frame.add(alignment)
        return frame

    def load_config(self):
        assert(os.path.exists(self.__grub_config_filename))
        d = config_dict(self.__grub_config_filename)
        self.kparams = {}
        if 'GRUB_CMDLINE_LINUX_DEFAULT' in d:
            re_kparam = re.compile("^([\w\.]+)=(.*)")
            kparam_str = d['GRUB_CMDLINE_LINUX_DEFAULT'].replace('"', '')
            for param in kparam_str.split(' '):
                value = 1
                m = re_kparam.match(param)
                if m:
                    param = m.group(1)
                    value = m.group(2)
                self.kparams[param] = value
        if 'GRUB_GFXPAYLOAD_LINUX' in d:
            re_kparam = re.compile("^([\w\.]+)=(.*)")
            value = d['GRUB_GFXPAYLOAD_LINUX'].replace('"', '')
            self.__grub_gfxpayload_linux = value
            if value == 'text':
                self.has_disable_grub_graphics(True)
            else:
                self.has_disable_grub_graphics(False)
        else:
            self.has_disable_grub_graphics(False)

        if 'drm.debug' in self.kparams:
            self.has_enable_debugging(True)
        else:
            self.has_enable_debugging(False)

        if 'splash' not in self.kparams:
            self.has_disable_splash(True)
        else:
            self.has_disable_splash(False)

        if 'vesafb.invalid' in self.kparams:
            self.has_disable_vesafb(True)
        else:
            self.has_disable_vesafb(False)

        if 'nopat' in self.kparams:
            self.has_disable_pat(True)
        else:
            self.has_disable_pat(False)

    def load_apport_config(self):
        path = "/etc/default/apport"
        if not os.path.exists(path):
            return

        d = config_dict(path)
        apport_enabled = d.get('enabled', None)
        if apport_enabled == '1':
            self.has_enable_apport(True)
        elif apport_enabled == '0':
            self.has_enable_apport(False)

    def has_enable_debugging(self, value=None):
        if value is not None:
            self.__enable_debugging = value
        elif self.__enable_debugging is None:
            self.load_config()
        return self.__enable_debugging
    def handle_enable_debugging(self, widget):
        self.has_enable_debugging(widget.get_active())

    def has_disable_splash(self, value=None):
        if value is not None:
            self.__disable_splash = value
        elif self.__disable_splash is None:
            self.load_config()
        return self.__disable_splash
    def handle_disable_splash(self, widget):
        self.has_disable_splash(widget.get_active())

    def has_disable_vesafb(self, value=None):
        if value is not None:
            self.__disable_vesafb = value
        elif self.__disable_vesafb is None:
            self.load_config()
        return self.__disable_vesafb
    def handle_disable_vesafb(self, widget):
        self.has_disable_vesafb(widget.get_active())

    def has_disable_pat(self, value=None):
        if value is not None:
            self.__disable_pat = value
        elif self.__disable_pat is None:
            self.load_config()
        return self.__disable_pat
    def handle_disable_pat(self, widget):
        self.has_disable_pat(widget.get_active())

    def has_enable_apport(self, value=None):
        if value is not None:
            self.__enable_apport = value
        elif self.__enable_apport is None:
            self.load_apport_config()
        return self.__enable_apport
    def handle_enable_apport(self, widget):
        active = widget.get_active()
        if active == self.__enable_apport:
            return
        print("Handling apport enabled")

        if self.has_enable_apport(widget.get_active()):
            enabled = 1
        else:
            enabled = 0

        filename = "/etc/default/apport"
        fd, temp_path = tempfile.mkstemp(text=True)
        os.chmod(temp_path, stat.S_IWUSR | stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        fo = os.fdopen(fd, "w+")
        config_update(filename, override_params={'enabled': enabled}, fileio=fo)
        fo.close()

        # Move new file into place
        shutil.move(temp_path, filename)
        os.chmod(filename, stat.S_IWUSR | stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)


    def has_disable_grub_graphics(self, value=None):
        if value is not None:
            self.__disable_grub_graphics = value
        elif self.__disable_grub_graphics is None:
            self.load_config()
        return self.__disable_grub_graphics
    def handle_disable_grub_graphics(self, widget):
        self.has_disable_grub_graphics(widget.get_active())

    def update_grub(self):
        try:
            subprocess.call(['/usr/sbin/update-grub'])
            return True
        except:
            # TODO: Indicate error occurred
            return False

    def on_report_bug_action(self, widget):
        process = subprocess.Popen(['ubuntu-bug', 'xorg'])
        process.communicate()

    def on_scan_errors(self, widget):
        re_xorg_error = re.compile("^\[\s*([\d\.]+)\] \(EE\) (.*)$")
        re_dmesg_error = re.compile("^\[\s*(\d+\.\d+)\] (.*(?:BUG|ERROR|WARNING).*)$")
        re_jockey_error = re.compile("^(\d+\-\d+-\d+ \d+:\d+:\d+,\d+) ERROR: (.*)$")
        errors = []

        # Xorg.0.log errors
        process = subprocess.Popen(['grep', '(EE)', '/var/log/Xorg.0.log'], universal_newlines=True)
        stdout, stderr = process.communicate()
        for err in str(stdout).split("\n"):
            m = re_jockey_error.match(err)
            if not m:
                continue
            timestamp = m.group(1)
            errmsg = m.group(2)
            errors.append(errmsg)

        # dmesg errors
        process = subprocess.Popen(['dmesg'], universal_newlines=True)
        stdout, stderr = process.communicate()
        for err in str(stdout).split("\n"):
            m = re_dmesg_error.match(err)
            if not m:
                continue
            timestamp = m.group(1)
            errmsg = m.group(2)
            errors.append(errmsg)

        # jockey errors
        if os.path.exists('/var/log/jockey.log'):
            process = subprocess.Popen(['grep', 'ERROR', '/var/log/jockey.log'], universal_newlines=True)
            stdout, stderr = process.communicate()
            for err in str(stdout).split("\n"):
                m = re_dmesg_error.match(err)
                if not m:
                    continue
                timestamp = m.group(1)
                errmsg = m.group(2)
                errors.append(errmsg)

        errors_window = ErrorsTreeView(errors)

    def on_apply(self, widget):
        overrides = {}
        merges = {}
        cmdline_default_params = self.kparams
        fd, temp_grub_path = tempfile.mkstemp(text=True)
        os.chmod(temp_grub_path, stat.S_IWUSR | stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        fo = os.fdopen(fd, "w+")
        if self.__disable_splash:
            if 'quiet' in cmdline_default_params:
                del cmdline_default_params['quiet']
            if 'splash' in cmdline_default_params:
                del cmdline_default_params['splash']
        else:
            cmdline_default_params['quiet'] = None
            cmdline_default_params['splash'] = None
        if self.__disable_pat:
            cmdline_default_params['nopat'] = None
        elif 'nopat' in cmdline_default_params:
            del cmdline_default_params['nopat']
        if self.__disable_vesafb:
            cmdline_default_params['vesafb.invalid'] = 1
        elif 'vesafb.invalid' in cmdline_default_params:
            del cmdline_default_params['vesafb.invalid']
        if self.__enable_debugging:
            # TODO: Enable debug for Xorg.0.log
            cmdline_default_params['drm.debug'] = '0xe'
            cmdline_default_params['plymouth:debug'] = None
        elif 'drm.debug' in cmdline_default_params:
            del cmdline_default_params['drm.debug']
        if self.__disable_grub_graphics is not None:
            # NOTE: Where text graphics works, this can be handled by blacklisting in grub.
            #       Should offer to file a request for this against grub maybe.
            if self.__disable_grub_graphics:
                overrides['GRUB_GFXPAYLOAD_LINUX'] = 'text'
            elif self.__grub_gfxpayload_linux != 'text':
                overrides['GRUB_GFXPAYLOAD_LINUX'] = self.__grub_gfxpayload_linux
            else:
                overrides['GRUB_GFXPAYLOAD_LINUX'] = 'keep'

        kparams = []
        for k,v in cmdline_default_params.items():
            if not k:
                continue
            elif v is None:
                kparams.append(k)
            else:
                kparams.append("%s=%s" %(k, v))
        overrides['GRUB_CMDLINE_LINUX_DEFAULT'] = '"%s"' %(' '.join(kparams))

        assert(os.path.exists(self.__grub_config_filename))
        config_update(self.__grub_config_filename, override_params=overrides, merge_params=merges, fileio=fo)

        fo.close()

        # Backup the old file
        try:
            bak_path = safe_backup(self.__grub_config_filename)
            if not bak_path:
                # TODO: Display error message dialog
                print("Error:  Could not backup file %s.  Changes not applied." %(
                    self.__grub_config_filename))
                return
        except IOError as err:
            # TODO: Display error message dialog
            print("Error:  Failure creating backup file for %s.  Changes not applied." %(
                self.__grub_config_filename))
            print(err)
            return

        # Move new file into place
        shutil.move(temp_grub_path, self.__grub_config_filename)
        os.chmod(self.__grub_config_filename, stat.S_IWUSR | stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

        # Finally, update grub
        # TODO: Only do this if we change any of the grub parameters
        self.update_grub()

        # TODO: Mark Apply button insensitive

    def run(self):
        Gtk.main()

    def on_close(self, widget=None, event=None, data=None):
        Gtk.main_quit()
        return False


# TODO: cmdline option to display grub file contents (--dryrun?)
