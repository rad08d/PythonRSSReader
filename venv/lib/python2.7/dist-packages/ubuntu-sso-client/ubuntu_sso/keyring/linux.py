# -*- coding: utf-8 -*-
#
# Copyright (C) 2010-2012 Canonical
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
"""Handle keys in the local kerying."""

try:
    # pylint: disable=E0611,F0401
    from urllib.parse import parse_qsl, urlencode
    # pylint: enable=E0611,F0401
except ImportError:
    from urllib import urlencode
    from urlparse import parse_qsl

from twisted.internet.defer import inlineCallbacks, returnValue

from ubuntu_sso.logger import setup_logging
from ubuntu_sso.utils.txsecrets import SecretService
from ubuntu_sso.keyring import (
    get_token_name,
    get_old_token_name,
    U1_APP_NAME,
    try_old_credentials)


logger = setup_logging("ubuntu_sso.keyring.linux")


class Keyring(object):
    """A Keyring for a given application name."""

    def __init__(self):
        """Initialize this instance."""
        self.service = SecretService()

    @inlineCallbacks
    def _find_keyring_item(self, app_name, attr=None):
        """Return the keyring item or None if not found."""
        if attr is None:
            attr = self._get_keyring_attr(app_name)
        logger.debug("Finding all items for app_name %r.", app_name)
        items = yield self.service.search_items(attr)
        if len(items) == 0:
            # if no items found, return None
            logger.debug("No items found!")
            returnValue(None)

        logger.debug("Returning first item found.")
        returnValue(items[0])

    def _get_keyring_attr(self, app_name):
        """Build the keyring attributes for this credentials."""
        attr = {"key-type": "Ubuntu SSO credentials",
                "token-name": get_token_name(app_name)}
        return attr

    @inlineCallbacks
    def set_credentials(self, app_name, cred):
        """Set the credentials of the Ubuntu SSO item."""
        # Creates the secret from the credentials
        secret = urlencode(cred)

        attr = self._get_keyring_attr(app_name)
        # Add our SSO credentials to the keyring
        yield self.service.open_session()
        collection = yield self.service.get_default_collection()
        yield collection.create_item(app_name, attr, secret, True)

    @inlineCallbacks
    def _migrate_old_token_name(self, app_name):
        """Migrate credentials with old name, store them with new name."""
        logger.debug("Migrating old token name.")
        attr = self._get_keyring_attr(app_name)
        attr['token-name'] = get_old_token_name(app_name)
        item = yield self._find_keyring_item(app_name, attr=attr)
        if item is not None:
            yield self.set_credentials(app_name,
                                       dict(parse_qsl(item.secret)))
            yield item.delete()

        result = yield self._find_keyring_item(app_name)
        returnValue(result)

    @inlineCallbacks
    def get_credentials(self, app_name):
        """A deferred with the secret of the SSO item in a dictionary."""
        # If we have no attributes, return None
        logger.debug("Getting credentials for %r.", app_name)
        yield self.service.open_session()
        item = yield self._find_keyring_item(app_name)
        if item is None:
            item = yield self._migrate_old_token_name(app_name)

        if item is not None:
            logger.debug("Parsing secret.")
            secret = yield item.get_value()
            returnValue(dict(parse_qsl(secret)))
        else:
            # if no item found, try getting the old credentials
            if app_name == U1_APP_NAME:
                logger.debug("Trying old credentials for %r.", app_name)
                old_creds = yield try_old_credentials(app_name)
                returnValue(old_creds)
        # nothing was found
        returnValue(None)

    @inlineCallbacks
    def delete_credentials(self, app_name):
        """Delete a set of credentials from the keyring."""
        attr = self._get_keyring_attr(app_name)
        # Add our SSO credentials to the keyring
        yield self.service.open_session()
        collection = yield self.service.get_default_collection()
        yield collection.create_item(app_name, attr, "secret!", True)

        item = yield self._find_keyring_item(app_name)
        if item is not None:
            yield item.delete()
