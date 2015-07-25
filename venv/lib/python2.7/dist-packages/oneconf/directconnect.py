# Copyright (C) 2010 Canonical
#
# Authors:
#  Didier Roche <didrocks@ubuntu.com>
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

from gettext import gettext as _

from oneconf.hosts import Hosts, HostError

import sys

class DirectConnect(object):

    """
    Dummy backend handling exit and exception directly
    """

    def _ensurePackageSetHandler(self):
        '''Ensure we import the package set handler at the right time'''
        from oneconf.packagesethandler import PackageSetHandler
        self.PackageSetHandler = PackageSetHandler

    def get_all_hosts(self):
        '''get a dict of all available hosts'''
        return Hosts().get_all_hosts()

    def set_share_inventory(self, share_inventory, hostid=None, hostname=None):
        '''update if we share the chosen host inventory on the server'''
        try:
            Hosts().set_share_inventory(share_inventory, hostid, hostname)
        except HostError as e:
            print(e)
            sys.exit(1)

    def get_packages(self, hostid, hostname, only_manual):
        '''trigger getpackages handling'''

        try:
            self._ensurePackageSetHandler()
            return self.PackageSetHandler().get_packages(
                hostid, hostname, only_manual)
        except HostError as e:
            print(e)
            sys.exit(1)

    def diff(self, hostid, hostname):
        '''trigger diff handling'''

        try:
            self._ensurePackageSetHandler()
            return self.PackageSetHandler().diff(hostid, hostname)
        except HostError as e:
            print(e)
            sys.exit(1)

    def update(self):
        '''trigger update handling'''
        try:
            self._ensurePackageSetHandler()
            self.PackageSetHandler().update()
        except HostError as e:
            print(e)
            sys.exit(1)

    def async_update(self):
        '''only used in fallback mode: no async notion for direct connexion'''
        self.update()

    def get_last_sync_date(self):
        '''get last time the store was successfully synced'''
        return Hosts().get_last_sync_date()

    def stop_service(self):
        '''kindly ask the oneconf service to stop (not relevant for a direct mode)'''
        print(_("Nothing done: in direct mode, there is no communication with the service"))
        sys.exit(1)
