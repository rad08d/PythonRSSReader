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
"""Implementations of different keyrings."""

from __future__ import unicode_literals

import socket
import sys

try:
    # pylint: disable=E0611,F0401
    from urllib.parse import quote
    # pylint: enable=E0611,F0401
except ImportError:
    from urllib import quote

from twisted.internet.defer import inlineCallbacks, returnValue

from ubuntu_sso.logger import setup_logging
from ubuntu_sso.utils import compat

logger = setup_logging("ubuntu_sso.keyring")

TOKEN_SEPARATOR = ' @ '
SEPARATOR_REPLACEMENT = ' AT '

U1_APP_NAME = "Ubuntu One"
U1_KEY_NAME = "UbuntuOne token for https://ubuntuone.com"
U1_KEY_ATTR = {
    "oauth-consumer-key": "ubuntuone",
    "ubuntuone-realm": "https://ubuntuone.com",
}


def gethostname():
    """Get the hostname, return the name as unicode."""
    sys_encoding = sys.getfilesystemencoding()
    hostname = socket.gethostname()
    if isinstance(hostname, compat.binary_type):
        return hostname.decode(sys_encoding)
    return hostname


def get_old_token_name(app_name):
    """Build the token name (old style). Return an unicode."""
    quoted_app_name = quote(app_name)
    computer_name = gethostname()
    quoted_computer_name = quote(computer_name)

    assert isinstance(computer_name, compat.text_type)
    assert isinstance(quoted_computer_name, compat.text_type)

    return "%s - %s" % (quoted_app_name, quoted_computer_name)


def get_token_name(app_name):
    """Build the token name.. Return an unicode."""
    computer_name = gethostname()
    computer_name = computer_name.replace(TOKEN_SEPARATOR,
                                          SEPARATOR_REPLACEMENT)

    assert isinstance(computer_name, compat.text_type)
    assert isinstance(computer_name, compat.text_type)

    return TOKEN_SEPARATOR.join((app_name, computer_name))


@inlineCallbacks
def try_old_credentials(app_name):
    """Try to get old U1 credentials and format them as new."""
    logger.debug('trying to get old credentials.')
    old_creds = yield UbuntuOneOAuthKeyring().get_credentials(U1_KEY_NAME)
    if old_creds is not None:
        # Old creds found, build a new credentials dict with them
        creds = {
            'consumer_key': "ubuntuone",
            'consumer_secret': "hammertime",
            'name': U1_KEY_NAME,
            'token': old_creds["oauth_token"],
            'token_secret': old_creds["oauth_token_secret"],
        }
        logger.debug('found old credentials')
        returnValue(creds)
    logger.debug('try_old_credentials: No old credentials for this app.')
    returnValue(None)


Keyring = None
if sys.platform in ('win32', 'darwin'):
    from ubuntu_sso.keyring import pykeyring
    Keyring = pykeyring.Keyring
else:
    from ubuntu_sso.keyring import linux as linux_kr
    Keyring = linux_kr.Keyring


class UbuntuOneOAuthKeyring(Keyring):
    """A particular Keyring for Ubuntu One."""

    def _get_keyring_attr(self, app_name):
        """Build the keyring attributes for this credentials."""
        return U1_KEY_ATTR
