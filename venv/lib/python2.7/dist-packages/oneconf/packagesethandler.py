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


import hashlib
import json
import logging
import os
from pprint import pformat

LOG = logging.getLogger(__name__)

from oneconf.hosts import Hosts
from oneconf.distributor import get_distro
from oneconf.paths import PACKAGE_LIST_PREFIX
from oneconf import utils

class PackageSetInitError(Exception):
    """An error occurred, preventing the package set to initialize."""


class PackageSetHandler(object):
    """
    Direct access to database for getting and updating the list
    """

    def __init__(self, hosts=None):

        self.hosts = hosts
        if not hosts:
            self.hosts = Hosts()
        self.distro = get_distro()
        if not self.distro:
            raise PackageSetInitError(
                "Can't initialize PackageSetHandler: no valid distro provided")
        self.last_storage_sync = None

        # create cache for storage package list, indexed by hostid
        self.package_list = {}


    def update(self):
        '''update the store with package list'''

        hostid = self.hosts.current_host['hostid']

        LOG.debug("Updating package list")
        newpkg_list = self.distro.compute_local_packagelist()

        LOG.debug("Creating the checksum")
        # We need to get a reliable checksum for the dictionary in
        # newpkg_list.  Dictionary order is unpredictable, so to get a
        # reproducible checksum, we need a predictable string representation
        # of the dictionary.  pprint.pformat() seems to give us the best
        # option here since it guarantees that dictionary keys are sorted.
        # hashlib works on bytes only though, so assume utf-8.
        hash_input = pformat(newpkg_list).encode('utf-8')
        checksum = hashlib.sha224(hash_input).hexdigest()

        LOG.debug("Package list need refresh")
        self.package_list[hostid] = {'valid': True, 'package_list': newpkg_list}
        utils.save_json_file_update(os.path.join(self.hosts.get_currenthost_dir(), '%s_%s' % (PACKAGE_LIST_PREFIX, hostid)),
                                    self.package_list[hostid]['package_list'])
        if self.hosts.current_host['packages_checksum'] != checksum:
            self.hosts.current_host['packages_checksum'] = checksum
            self.hosts.save_current_host()
        LOG.debug("Update done")

    def get_packages(self, hostid=None, hostname=None, only_manual=False):
        '''get all installed packages from the storage'''

        hostid = self.hosts.get_hostid_from_context(hostid, hostname)
        LOG.debug ("Request for package list for %s with only manual packages reduced scope to: %s", hostid, only_manual)
        package_list = self._get_installed_packages(hostid)
        if only_manual:
            package_list = [
                package_elem for package_elem in package_list
                if not package_list[package_elem]["auto"]]
        return package_list

    def _get_installed_packages(self, hostid):
        '''get installed packages from the storage or cache

        Return: uptodate package_list'''

        need_reload = False
        try:
            if self.package_list[hostid]['valid']:
                LOG.debug("Hit cache for package list")
                package_list = self.package_list[hostid]['package_list']
            else:
                need_reload = True
        except KeyError:
            need_reload = True

        if need_reload:
            self.package_list[hostid] = {
                'valid': True,
                'package_list': self._get_packagelist_from_store(hostid),
                }
        return self.package_list[hostid]['package_list']


    def diff(self, distant_hostid=None, distant_hostname=None):
        """get a diff from current package state from another host

        This function can be use to make a diff between all packages installed
        on both computer, use_cache

        Return: (packages_to_install (packages in distant_hostid not in local_hostid),
                 packages_to_remove (packages in local hostid not in distant_hostid))
        """

        distant_hostid = self.hosts.get_hostid_from_context(
            distant_hostid, distant_hostname)

        LOG.debug("Collecting all installed packages on this system")
        local_package_list = set(
            self.get_packages(self.hosts.current_host['hostid'], False))

        LOG.debug("Collecting all installed packages on the other system")
        distant_package_list = set(self.get_packages(distant_hostid, False))

        LOG.debug("Comparing")
        packages_to_install = [
            x for x in sorted(distant_package_list)
            if x not in local_package_list]
        packages_to_remove = [
            x for x in sorted(local_package_list)
            if x not in distant_package_list]

        # for Dbus which doesn't like empty list
        if not packages_to_install:
            packages_to_install = ''
        if not packages_to_remove:
            packages_to_remove = ''

        return packages_to_install, packages_to_remove


    def _get_packagelist_from_store(self, hostid):
        '''load package list for every computer in cache'''

        LOG.debug('get package list from store for hostid: %s' % hostid)

        # load current content in cache
        try:
            with open(os.path.join(self.hosts.get_currenthost_dir(), '%s_%s' % (PACKAGE_LIST_PREFIX, hostid)), 'r') as f:
                # can be none in corrupted null file
                pkg_list = json.load(f)
        except (IOError, ValueError):
            LOG.warning ("no valid package list stored for hostid: %s" % hostid)
            pkg_list = None

        if pkg_list is None:
            pkg_list = {}
            # there is no way that no package is installed in current host
            # At least, there is oneconf ;) Ask for refresh
            if hostid == self.hosts.current_host['hostid']:
                LOG.debug ("Processing first update for current host")
                self.update()
                pkg_list = self.package_list[hostid]['package_list']

        return pkg_list
