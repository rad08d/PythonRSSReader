# -*- coding: utf-8 -*-
#
# Copyright 2011-2013 Canonical Ltd.
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
"""The common bits of a webclient."""

import collections

from httplib2 import iri2uri
from oauthlib.oauth1 import (
    Client, SIGNATURE_HMAC, SIGNATURE_PLAINTEXT, SIGNATURE_TYPE_AUTH_HEADER,
    SIGNATURE_TYPE_QUERY)
from twisted.internet import defer

from ubuntu_sso import (USER_SUCCESS,
                        UI_PROXY_CREDS_DIALOG,
                        UI_SSL_DIALOG)
from ubuntu_sso.logger import setup_logging
from ubuntu_sso.utils.runner import spawn_program
from ubuntu_sso.utils.ui import SSL_DETAILS_TEMPLATE
from ubuntu_sso.utils.webclient.timestamp import TimestampChecker


logger = setup_logging("ubuntu_sso.utils.webclient.common")


class WebClientError(Exception):
    """An http error happened while calling the webservice."""


class UnauthorizedError(WebClientError):
    """The request ended with bad_request, unauthorized or forbidden."""


class ProxyUnauthorizedError(WebClientError):
    """Failure raised when there is an issue with the proxy auth."""


class Response(object):
    """A response object."""

    def __init__(self, content, headers=None):
        """Initialize this instance."""
        self.content = content
        self.headers = headers


class HeaderDict(collections.defaultdict):
    """A case insensitive dict for headers."""

    # pylint: disable=E1002
    def __init__(self, *args, **kwargs):
        """Handle case-insensitive keys."""
        super(HeaderDict, self).__init__(list, *args, **kwargs)
        # pylint: disable=E1101
        for key, value in self.items():
            super(HeaderDict, self).__delitem__(key)
            self[key] = value

    def __setitem__(self, key, value):
        """Set the value with a case-insensitive key."""
        super(HeaderDict, self).__setitem__(key.lower(), value)

    def __getitem__(self, key):
        """Get the value with a case-insensitive key."""
        return super(HeaderDict, self).__getitem__(key.lower())

    def __delitem__(self, key):
        """Delete the item with the case-insensitive key."""
        super(HeaderDict, self).__delitem__(key.lower())

    def __contains__(self, key):
        """Check the containment with a case-insensitive key."""
        return super(HeaderDict, self).__contains__(key.lower())


class BaseWebClient(object):
    """The webclient base class, to be extended by backends."""

    timestamp_checker = None

    def __init__(self, appname='', username=None, password=None,
                 oauth_sign_plain=False):
        """Initialize this instance."""
        self.appname = appname
        self.username = username
        self.password = password
        self.proxy_username = None
        self.proxy_password = None
        self.oauth_sign_plain = oauth_sign_plain

    def request(self, iri, method="GET", extra_headers=None,
                oauth_credentials=None, post_content=None):
        """Return a deferred that will be fired with a Response object."""
        raise NotImplementedError

    @classmethod
    def get_timestamp_checker(cls):
        """Get the timestamp checker for this class of webclient."""
        if cls.timestamp_checker is None:
            cls.timestamp_checker = TimestampChecker(cls)
        return cls.timestamp_checker

    def get_timestamp(self):
        """Get a timestamp synchronized with the server."""
        return self.get_timestamp_checker().get_faithful_time()

    def force_use_proxy(self, settings):
        """Setup this webclient to use the given proxy settings."""
        raise NotImplementedError

    def iri_to_uri(self, iri):
        """Transform a unicode iri into a ascii uri."""
        if not isinstance(iri, unicode):
            raise TypeError('iri %r should be unicode.' % iri)
        return bytes(iri2uri(iri))

    def build_oauth_request(self, method, uri, credentials, timestamp,
                            parameters=None, as_query=True):
        """Build an oauth request given some credentials."""

        # oauthlib is requiring the timestamp to be a string, because
        # it tries to escape all the parameters.
        oauth_client = Client(credentials['consumer_key'],
                              credentials['consumer_secret'],
                              credentials['token'],
                              credentials['token_secret'],
                              signature_method=(SIGNATURE_PLAINTEXT
                                                if self.oauth_sign_plain
                                                else SIGNATURE_HMAC),
                              signature_type=(SIGNATURE_TYPE_QUERY
                                              if as_query
                                              else SIGNATURE_TYPE_AUTH_HEADER),
                              timestamp=str(timestamp))

        try:
            url, signed_headers, body = oauth_client.sign(
                uri, method, parameters if parameters is not None else {},
                {'Content-Type': 'application/x-www-form-urlencoded'})
        except ValueError:
            url, signed_headers, body = oauth_client.sign(uri, method)

        return url, signed_headers, body

    @defer.inlineCallbacks
    def build_request_headers(self, uri, method="GET", extra_headers=None,
                              oauth_credentials=None):
        """Build the headers for a request."""
        if extra_headers:
            headers = dict(extra_headers)
        else:
            headers = {}

        if oauth_credentials:
            timestamp = yield self.get_timestamp()
            url, signed_headers, body = self.build_oauth_request(
                method, uri, oauth_credentials, timestamp,
                as_query=False)
            headers.update(signed_headers)

        defer.returnValue(headers)

    @defer.inlineCallbacks
    def build_signed_iri(self, iri, credentials, parameters=None):
        """Build a new iri signing 'iri' with 'credentials'."""
        uri = self.iri_to_uri(iri)
        timestamp = yield self.get_timestamp()
        url, signed_headers, body = self.build_oauth_request(
            method='GET', uri=uri, credentials=credentials,
            timestamp=timestamp, parameters=parameters)
        defer.returnValue(url)

    def shutdown(self):
        """Shut down all pending requests (if possible)."""

    @defer.inlineCallbacks
    def _load_proxy_creds_from_keyring(self, domain):
        """Load the proxy creds from the keyring."""
        from ubuntu_sso.keyring import Keyring
        keyring = Keyring()
        try:
            creds = yield keyring.get_credentials(str(domain))
            logger.debug('Got credentials from keyring.')
        except Exception as e:
            logger.error('Error when retrieving the creds.')
            raise WebClientError('Error when retrieving the creds.', e)
        if creds is not None:
            # if we are loading the same creds it means that we got the wrong
            # ones
            if (self.proxy_username == creds['username'] and
                    self.proxy_password == creds['password']):
                defer.returnValue(False)
            else:
                self.proxy_username = creds['username']
                self.proxy_password = creds['password']
                defer.returnValue(True)
        logger.debug('Proxy creds not in keyring.')
        defer.returnValue(False)

    def _launch_proxy_creds_dialog(self, domain, retry):
        """Launch the dialog used to get the creds."""
        from ubuntu_sso.utils import get_bin_cmd
        args = get_bin_cmd(UI_PROXY_CREDS_DIALOG)

        args += ['--domain', domain]
        if retry:
            args += ['--retry']
        return spawn_program(args)

    @defer.inlineCallbacks
    def request_proxy_auth_credentials(self, domain, retry):
        """Request the auth creds to the user."""
        if not retry:
            if (self.proxy_username is not None
                    and self.proxy_password is not None):
                logger.debug('Not retry and credentials are present.')
                defer.returnValue(True)
            else:
                creds_loaded = yield self._load_proxy_creds_from_keyring(
                    domain)
                if creds_loaded:
                    defer.returnValue(True)

        try:
            return_code = yield self._launch_proxy_creds_dialog(domain, retry)
        except Exception as e:
            logger.error('Error when running external ui process.')
            raise WebClientError('Error when running external ui process.', e)

        if return_code == USER_SUCCESS:
            creds_loaded = yield self._load_proxy_creds_from_keyring(domain)
            defer.returnValue(creds_loaded)
        else:
            logger.debug('Could not retrieve the credentials. Return code: %r',
                         return_code)
            defer.returnValue(False)

    def format_ssl_details(self, details):
        """Return a formatted string with the details."""
        return SSL_DETAILS_TEMPLATE % details

    def _launch_ssl_dialog(self, domain, details):
        """Launch a dialog used to approve the ssl cert."""
        from ubuntu_sso.utils import get_bin_cmd

        args = get_bin_cmd(UI_SSL_DIALOG)
        args += ['--domain', domain,
                 '--details', details,
                 '--appname', self.appname]

        return spawn_program(args)

    def _was_ssl_accepted(self, cert_details):
        """Return if the cert was already accepted."""
        # TODO: Ensure that we look at pinned certs in a following branch
        return False

    @defer.inlineCallbacks
    def request_ssl_cert_approval(self, domain, details):
        """Request the user for ssl approval."""
        if self._was_ssl_accepted(details):
            defer.returnValue(True)

        return_code = yield self._launch_ssl_dialog(domain, details)
        defer.returnValue(return_code == USER_SUCCESS)
