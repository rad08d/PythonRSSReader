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

import apt
import logging

LOG = logging.getLogger(__name__)

from oneconf.distributor import Distro


class Ubuntu(Distro):

    ONECONF_SERVER = "https://apps.ubuntu.com/cat/api/1.0"

    def compute_local_packagelist(self):
        '''Introspect what's installed on this hostid

        Return: installed_packages list
        '''
        
        LOG.debug ('Compute package list for current host')

        # get list of all apps installed
        installed_packages = {}

        with apt.Cache() as apt_cache:
            for pkg in apt_cache:
                if pkg.is_installed:
                    installed_packages[pkg.name] = {"auto": pkg.is_auto_installed}

        return installed_packages
        
