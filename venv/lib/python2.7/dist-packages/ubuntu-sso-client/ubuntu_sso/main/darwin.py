# -*- coding: utf-8 -*-
#
# Copyright 2009-2012 Canonical Ltd.
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
"""Main module implementation specific for darwin (OS X).

This module should never import from the multiplatform one (main/__init__.py),
but the other way around. Likewise, this module should *not* have any logic
regarding error processing or decision making about when to send a given
signal.

Also, most of the logging is being made in the main module to avoid
duplication between the different platform implementations.

"""

import os
import os.path

from dirspec import basedir
from twisted.internet import defer

from ubuntu_sso import BACKEND_EXECUTABLE
from ubuntu_sso.logger import setup_logging
from ubuntu_sso.utils import get_bin_cmd
from ubuntu_sso.utils.ipc import BaseClient
from ubuntu_sso.main.perspective_broker import (
    SSO_SERVICE_NAME,
    SSOLoginClient,
    CredentialsManagementClient,
    UbuntuSSOProxyBase,
)

# Invalid name for signals that are CamelCase
# pylint: disable=C0103


logger = setup_logging("ubuntu_sso.main.darwin")
SSO_INSTALL_PATH = 'SSOInstallPath'


def get_sso_domain_socket():
    """Compute the domain socket for the sso ipc."""
    path = os.path.join(basedir.xdg_cache_home, 'sso', 'ipc')
    return path


class DescriptionFactory(object):
    """Factory that provides the server and client descriptions."""

    client_description_pattern = 'unix:path=%s'
    server_description_pattern = 'unix:%s'

    def __init__(self):
        """Create a new instance."""
        self.domain = get_sso_domain_socket()
        self.server = self.server_description_pattern % self.domain
        self.client = self.client_description_pattern % self.domain


class UbuntuSSOProxy(UbuntuSSOProxyBase):
    """Object that exposes the diff referenceable objects."""

    name = SSO_SERVICE_NAME

    @property
    def description(self):
        """Get the description on which the SSO pb is running."""
        return DescriptionFactory()

    @property
    def cmdline(self):
        """Get the command line to activate an executable."""
        return get_bin_cmd(BACKEND_EXECUTABLE)


class UbuntuSSOClient(BaseClient):
    """Base client that provides remote access to the sso API."""

    name = SSO_SERVICE_NAME

    clients = {
        'sso_login': SSOLoginClient,
        'cred_manager': CredentialsManagementClient,
    }

    service_name = UbuntuSSOProxy.name
    service_description = UbuntuSSOProxy.description
    service_cmdline = UbuntuSSOProxy.cmdline


@defer.inlineCallbacks
def get_sso_client():
    """Get a client to access the SSO service."""
    result = UbuntuSSOClient()
    yield result.connect()
    defer.returnValue(result)
