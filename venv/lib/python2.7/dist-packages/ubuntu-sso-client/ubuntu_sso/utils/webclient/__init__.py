# -*- coding: utf-8 -*-
#
# Copyright 2011-2012 Canonical Ltd.
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
"""A common webclient that can use a QtNetwork or libsoup backend."""

import sys


def is_qt4reactor_installed():
    """Check if the qt4reactor is installed."""
    result = False

    if not 'PyQt4' in sys.modules:
        return result

    try:
        from PyQt4.QtCore import QCoreApplication
        from PyQt4.QtGui import QApplication

        # we could be running a process with or without ui, and those are diff
        # apps.
        result = (QCoreApplication.instance() is not None
                   or QApplication.instance() is not None)
    except ImportError:
        pass

    return result


def webclient_module():
    """Choose the module of the web client."""
    if is_qt4reactor_installed():
        from ubuntu_sso.utils.webclient import qtnetwork
        return qtnetwork
    else:
        from ubuntu_sso.utils.webclient import libsoup
        #from ubuntu_sso.utils.webclient import txweb as web_module
        return libsoup


def webclient_factory(*args, **kwargs):
    """Choose the type of the web client dynamically."""
    web_module = webclient_module()
    return web_module.WebClient(*args, **kwargs)
