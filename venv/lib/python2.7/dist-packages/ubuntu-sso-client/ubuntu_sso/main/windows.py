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
"""Main module implementation specific for windows.

This module should never import from the multiplatform one (main/__init__.py),
but the other way around. Likewise, this module should *not* have any logic
regarding error processing or decision making about when to send a given
signal.

Also, most of the logging is being made in the main module to avoid
duplication between the different platform implementations.

"""
# pylint: disable=F0401
import win32process
import win32security
# pylint: enable=F0401

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


logger = setup_logging("ubuntu_sso.main.windows")
U1_REG_PATH = r'Software\Ubuntu One'
SSO_INSTALL_PATH = 'SSOInstallPath'
SSO_BASE_PB_PORT = 50000
SSO_RESERVED_PORTS = 3000
SSO_PORT_ALLOCATION_STEP = 3  # contiguous ports for sso, u1client, and u1cp


def get_user_id():
    """Compute the user id of the currently running process."""
    process_handle = win32process.GetCurrentProcess()
    token_handle = win32security.OpenProcessToken(process_handle,
                                              win32security.TOKEN_ALL_ACCESS)
    user_sid = win32security.GetTokenInformation(token_handle,
                                              win32security.TokenUser)[0]
    sid_parts = str(user_sid).split("-")
    return int(sid_parts[-1])


def get_sso_pb_port():
    """Compute the port the SSO service should run on per-user."""
    uid_modulo = get_user_id() % SSO_RESERVED_PORTS
    return SSO_BASE_PB_PORT + uid_modulo * SSO_PORT_ALLOCATION_STEP


class DescriptionFactory(object):
    """Factory that provides the server and client descriptions."""

    client_description_pattern = 'tcp:host=127.0.0.1:port=%s'
    server_description_pattern = 'tcp:%s:interface=127.0.0.1'

    def __init__(self):
        """Create a new instance."""
        self.port = get_sso_pb_port()
        self.server = self.server_description_pattern % self.port
        self.client = self.client_description_pattern % self.port


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
