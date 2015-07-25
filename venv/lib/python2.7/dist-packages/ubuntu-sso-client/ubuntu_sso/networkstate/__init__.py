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
"""Platform specific network status."""

import sys

# ignore global naming issues.
# pylint: disable=C0103

NetworkManagerState = None


class NetworkFailException(Exception):

    """Exception for when the network detect process fails."""


if sys.platform == 'win32':
    from ubuntu_sso.networkstate import windows
    networksource = windows
elif sys.platform == 'darwin':
    from ubuntu_sso.networkstate import darwin
    networksource = darwin
else:
    from ubuntu_sso.networkstate import linux
    networksource = linux

NetworkManagerState = networksource.NetworkManagerState
is_machine_connected = networksource.is_machine_connected
