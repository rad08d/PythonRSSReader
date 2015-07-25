# -*- coding: utf-8 -*-
#
# Copyright 2012-2013 Canonical Ltd.
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
"""Qt main loop runner."""

# pylint: disable=E0611,F0401

import sys

# pylint: disable=W0621
import dbus.mainloop.qt
# pylint: enable=W0621

from PyQt4 import QtCore

from ubuntu_sso.utils.locale import fix_turkish_locale


TIMERS = set()


def timeout_func(interval, callback, *a, **kw):
    """Delay import of dynamic bindings to avoid crashes."""

    # QTimers don't support priorities
    kw.pop("priority", None)

    timer = QtCore.QTimer()
    TIMERS.add(timer)

    def _callback():
        """Call the real callback, with arguments, until it returns False."""
        if timer in TIMERS:
            result = callback(*a, **kw)
            if not result:
                timer.stop()
                TIMERS.remove(timer)
                # Probably overkill
                timer.deleteLater()

    timer.timeout.connect(_callback)
    timer.start(interval)


def shutdown_func(*a, **kw):
    """Delay import of dynamic bindings to avoid crashes."""
    QtCore.QCoreApplication.instance().exit()


def start_setup():
    """Setup the env to run the service."""
    fix_turkish_locale()
    # this has to be created before calling dbus.mainloop.qt.DBusQtMainLoop
    loop = QtCore.QCoreApplication(sys.argv)
    dbus.mainloop.qt.DBusQtMainLoop(set_as_default=True)
    return loop


def run_func(loop):
    """Delay import of dynamic bindings to avoid crashes."""
    loop.exec_()
