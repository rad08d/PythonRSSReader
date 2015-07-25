# -*- coding: utf-8 -*-

# Copyright (C) 2011 Canonical
#
# Authors:
#  Didier Roche
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; version 3.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

"""For the test suite.

See test/test_syncing.py
"""

import os
import sys
import logging

from gi.repository import GLib

from oneconf.paths import WEBCATALOG_SILO_SOURCE
from . import SyncHandler
from .infraclient_fake import WebCatalogAPI
from ..hosts import Hosts


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    from dbus.mainloop.glib import DBusGMainLoop
    DBusGMainLoop(set_as_default=True)

    os.environ["ONECONF_SINGLE_SYNC"] = "True"

    infraclient = None
    if not "--no-infra-client" in sys.argv:
        infraclient = WebCatalogAPI(WEBCATALOG_SILO_SOURCE)

    sync_handler = SyncHandler(Hosts(), infraclient=infraclient)
    loop = GLib.MainLoop()
    GLib.timeout_add_seconds(15, loop.quit)

    loop.run()
