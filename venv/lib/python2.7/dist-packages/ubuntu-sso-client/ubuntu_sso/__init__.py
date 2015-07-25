#
# Copyright 2009-2013 Canonical Ltd.
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
"""Ubuntu Single Sign On client code."""

import os


# Host URL changing environment variables
SSO_AUTH_BASE_URL = os.environ.get(
    'SSO_AUTH_BASE_URL', 'https://login.ubuntu.com')
SSO_UONE_BASE_URL = os.environ.get(
    'SSO_UONE_BASE_URL', 'https://one.ubuntu.com')

# DBus constants
DBUS_BUS_NAME = "com.ubuntu.sso"

DBUS_ACCOUNT_PATH = "/com/ubuntu/sso/accounts"
DBUS_IFACE_USER_NAME = "com.ubuntu.sso.UserManagement"

DBUS_CREDENTIALS_PATH = "/com/ubuntu/sso/credentials"
DBUS_CREDENTIALS_IFACE = "com.ubuntu.sso.CredentialsManagement"

NO_OP = lambda *args, **kwargs: None

# return codes for UIs
USER_SUCCESS = 0
USER_CANCELLATION = 10
EXCEPTION_RAISED = 11

BACKEND_EXECUTABLE = 'ubuntu-sso-login'

# available UIs
UI_SSL_DIALOG = 'ubuntu-sso-ssl-certificate-qt'
UI_EXECUTABLE_QT = 'ubuntu-sso-login-qt'
UI_PROXY_CREDS_DIALOG = 'ubuntu-sso-proxy-creds-qt'
