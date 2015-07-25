# -*- coding: utf-8 -*-
#
# Copyright 2012 Canonical Ltd.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# In addition, as a special exception, the copyright holders give
# permission to link the code of portions of this program with the
# OpenSSL library under certain conditions as described in each
# individual source file, and distribute linked combinations
# including the two.
# You must obey the GNU General Public License in all respects
# for all of the code used other than OpenSSL.  If you modify
# file(s) with this exception, you may extend this exception to your
# version of the file(s), but you are not obligated to do so.  If you
# do not wish to do so, delete this exception statement from your
# version.  If you delete this exception statement from all source
# files in the program, then also delete it here.
"""GLib main loop runner."""

# pylint: disable=E0611,F0401

from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

GLIB_MAINLOOP = None  # global


def timeout_func(*a, **kw):
    """Delay import of dynamic bindings to avoid crashes."""
    return GLib.timeout_add(*a, **kw)


def shutdown_func(*a, **kw):
    """Delay import of dynamic bindings to avoid crashes."""
    GLIB_MAINLOOP.quit()


def run_func(loop):
    """Delay import of dynamic bindings to avoid crashes."""
    loop.run()


def start_setup():
    """Setup the env to run the service."""
    DBusGMainLoop(set_as_default=True)
    global GLIB_MAINLOOP  # pylint: disable=W0603
    GLIB_MAINLOOP = loop = GLib.MainLoop()
    return loop
