# Copyright (C) 2009-2010 Canonical
#
# Authors:
#  Michael Vogt
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

import logging
import subprocess

try:
    from configparser import NoSectionError, RawConfigParser
except ImportError:
    # Python 2
    from ConfigParser import NoSectionError, RawConfigParser
from importlib import import_module
from oneconf.paths import ONECONF_OVERRIDE_FILE

LOG = logging.getLogger(__name__)


class Distro(object):
    """ abstract base class for a distribution """

    def compute_local_packagelist(self):
        '''Introspect what's installed on this hostid

        Return: installed_packages list
        '''
        raise NotImplementedError


def _get_distro():
    config = RawConfigParser()
    try:
        config.read(ONECONF_OVERRIDE_FILE)
        distro_id = config.get('TestSuite', 'distro')
    except NoSectionError:
        distro_id = subprocess.Popen(
            ["lsb_release","-i","-s"],
            stdout=subprocess.PIPE,
            universal_newlines=True).communicate()[0].strip()
    LOG.debug("get_distro: '%s'" % distro_id)
    # start with a import, this gives us only a oneconf module
    try:
        module =  import_module('.' + distro_id, 'oneconf.distributor')
        # get the right class and instanciate it
        distro_class = getattr(module, distro_id)
        instance = distro_class()
    except ImportError:
        LOG.warn("invalid distro: '%s'" % distro_id)
        return None
    return instance

def get_distro():
    """ factory to return the right Distro object """
    return distro_instance

# singleton
distro_instance=_get_distro()


if __name__ == "__main__":
    print(get_distro())
