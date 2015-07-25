#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""gstinstaller - install GStreamer components via PackageKit session service"""
# Copyright (C) 2010 Sebastian Heinlein <devel@glatzor.de>
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

from gettext import gettext as _
import logging
import optparse
import re
import sys

import dbus

from core import PACKAGEKIT_MODIFY_DBUS_INTERFACE, \
                 PACKAGEKIT_DBUS_PATH, \
                 PACKAGEKIT_DBUS_SERVICE
import errors

logging.basicConfig(format="%(levelname)s:%(message)s")
log = logging.getLogger("GStreamerInstaller")


class GStreamerInstaller(object):

    """Provides an installer of GStreamer components"""

    def __init__(self, xid, codecs):
        log.info("Initializing GStreamerInstaller")
        self.xid = dbus.UInt32(xid)
        self.provides = self._get_provides(codecs)
        bus = dbus.SessionBus()
        self.pk = bus.get_object(PACKAGEKIT_DBUS_SERVICE,
                                 PACKAGEKIT_DBUS_PATH, False)

    def _get_provides(self, codecs):
        provides = dbus.Array(signature="s")
        # E.g. "gstreamer|0.10|totem|Windows Media Video 9 decoder|
        #       decoder-video/x-wmv, wmvversion=(int)3, fourcc=(fourcc)WVC1,
        #       format=(fourcc)WVC1"
        # See http://gstreamer.freedesktop.org/data/doc/gstreamer/head/
        #             gst-plugins-base-libs/html/
        #             gst-plugins-base-libs-gstpbutilsinstallplugins.html
        regex = re.compile("^gstreamer\|(?P<major>[0-9])+\.(?P<minor>[0-9]+)\|"
                           "(?P<app>.+)\|(?P<desc>.+)\|(?P<type>[a-z]+?)-"
                           "(?P<name>.+?)(,(?P<fields>.+))?[|]?$")
        for codec in codecs:
            match = regex.match(codec)
            if not match:
                log.warn("Ignoring codec: %s", codec)
                continue
            provide = "%s|gstreamer%s.%s(%s-%s)" % (match.group("desc"),
                                                    match.group("major"),
                                                    match.group("minor"),
                                                    match.group("type"),
                                                    match.group("name"))
            if match.group("fields"):
                for field in match.group("fields").split(","):
                    provide += "(%s)" % field.strip()
            log.debug("Add provide: %s", provide)
            provides.append(provide)
        return provides

    @errors.convert_dbus_exception
    def run(self):
        self.pk.InstallGStreamerResources(self.xid, self.provides,
                                "hide-finished", timeout=360000,
                                dbus_interface=PACKAGEKIT_MODIFY_DBUS_INTERFACE)


def main():
    parser = optparse.OptionParser()
    parser.add_option("", "--transient-for", action="store", type="int",
                      dest="xid", default="0",
                      help=_("The X Window ID of the calling application"))
    options, args = parser.parse_args()
    installer = GStreamerInstaller(options.xid, args)
    # See the documentation of gstpbutilsinstallplugins for the exit state
    # definitions. Unluckily the PackageKit session interface doesn't support
    # partial codec installation
    try:
        installer.run()
    except errors.ModifyCancelled:
        log.warn("Cancelled")
        sys.exit(4)
    except errors.ModifyNoPackagesFound:
        log.critical("Could not find any packages to operate on")
        sys.exit(1)
    except Exception, error:
        log.exception(error)
        sys.exit(2)
    log.info("Finished succesfully")
    sys.exit(0)

if __name__ == "__main__":
    log.setLevel(logging.DEBUG)
    main()

# vim:ts=4:sw=4:et
