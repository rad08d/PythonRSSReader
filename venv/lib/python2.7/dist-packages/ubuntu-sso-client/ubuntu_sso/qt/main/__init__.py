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
"""Main module to open the QT UI."""

import os
import sys

from PyQt4 import QtGui, QtCore

# Module used to include the resources into this file
from ubuntu_sso.qt.ui import resources_rc
from ubuntu_sso.qt.ubuntu_sso_wizard import UbuntuSSOClientGUI
from ubuntu_sso.utils import compat, PLATFORM_QSS


# Poke resources_rc to avoid pyflakes complaining about unused import
assert(resources_rc)

if sys.platform in ('win32', 'darwin'):
    from ubuntu_sso.qt.main import windows
    source = windows
else:
    from ubuntu_sso.qt.main import linux
    source = linux


def main(**kwargs):
    """Start the QT mainloop and open the main window."""
    if os.environ.get('TESTABILITY', False) and \
            '-testability' not in sys.argv:
        sys.argv.append('-testability')
    app = QtGui.QApplication(sys.argv)

    source.main(app)

    data = []
    for qss_name in (PLATFORM_QSS, ":/stylesheet.qss"):
        qss = QtCore.QResource(qss_name)
        data.append(compat.text_type(qss.data()))
    app.setStyleSheet('\n'.join(data))

    # Fix the string that contains unicode chars.
    for key in kwargs:
        value = kwargs[key]
        if isinstance(value, compat.binary_type):
            kwargs[key] = value.decode('utf-8')

    close_callback = lambda: source.main_quit(app)
    ui = UbuntuSSOClientGUI(close_callback=close_callback, **kwargs)
    style = QtGui.QStyle.alignedRect(
                    QtCore.Qt.LeftToRight, QtCore.Qt.AlignCenter,
                    ui.size(), app.desktop().availableGeometry())
    ui.setGeometry(style)

    app = QtGui.QApplication.instance()
    app.setWindowIcon(QtGui.QIcon.fromTheme("ubuntuone"))

    ui.show()
    if sys.platform == 'darwin':
        ui.raise_()

    source.main_start(app)
