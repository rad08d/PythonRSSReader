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
"""A webclient backend that uses libsoup."""

import httplib

from twisted.internet import defer

from ubuntu_sso.logger import setup_logging
from ubuntu_sso.utils.webclient.common import (
    BaseWebClient,
    HeaderDict,
    Response,
    ProxyUnauthorizedError,
    UnauthorizedError,
    WebClientError,
)

URI_ANONYMOUS_TEMPLATE = "http://{host}:{port}/"
URI_USERNAME_TEMPLATE = "http://{username}:{password}@{host}:{port}/"

logger = setup_logging("ubuntu_sso.utils.webclient.libsoup")


class WebClient(BaseWebClient):
    """A webclient with a libsoup backend."""

    def __init__(self, *args, **kwargs):
        """Initialize this instance."""
        super(WebClient, self).__init__(*args, **kwargs)
        # pylint: disable=E0611,F0401
        from gi.repository import Soup, SoupGNOME
        self.soup = Soup
        self.session = Soup.SessionAsync()
        self.session.add_feature(SoupGNOME.ProxyResolverGNOME())
        self.session.connect("authenticate", self._on_authenticate)

    def _on_message(self, session, message, d):
        """Handle the result of an http message."""
        logger.debug('_on_message status code is %s', message.status_code)
        if message.status_code == httplib.OK:
            headers = HeaderDict()
            response_headers = message.get_property("response-headers")
            add_header = lambda key, value, _: headers[key].append(value)
            response_headers.foreach(add_header, None)
            content = message.response_body.flatten().get_data()
            response = Response(content, headers)
            d.callback(response)
        elif message.status_code == httplib.UNAUTHORIZED:
            e = UnauthorizedError(message.reason_phrase)
            d.errback(e)
        elif message.status_code == httplib.PROXY_AUTHENTICATION_REQUIRED:
            e = ProxyUnauthorizedError(message.reason_phrase)
            d.errback(e)
        else:
            e = WebClientError(message.reason_phrase)
            d.errback(e)

    @defer.inlineCallbacks
    def _on_authenticate(self, session, message, auth, retrying, data=None):
        """Handle the "authenticate" signal."""
        self.session.pause_message(message)
        try:
            logger.debug('_on_authenticate: message status code is %s',
                         message.status_code)
            if not retrying and self.username and self.password:
                auth.authenticate(self.username, self.password)
            if auth.is_for_proxy():
                logger.debug('_on_authenticate auth is for proxy.')
                got_creds = yield self.request_proxy_auth_credentials(
                    self.session.props.proxy_uri.host,
                    retrying)
                if got_creds:
                    logger.debug('Got proxy credentials from user.')
                    auth.authenticate(self.proxy_username, self.proxy_password)
        finally:
            self.session.unpause_message(message)

    @defer.inlineCallbacks
    def _on_proxy_authenticate(self, failure, iri, method="GET",
                extra_headers=None, oauth_credentials=None, post_content=None):
        """Deal with wrong settings."""
        failure.trap(ProxyUnauthorizedError)
        logger.debug('Proxy settings are wrong.')
        got_creds = yield self.request_proxy_auth_credentials(
            self.session.props.proxy_uri.host,
            True)
        if got_creds:
            settings = dict(host=self.session.props.proxy_uri.host,
                            port=self.session.props.proxy_uri.port,
                            username=self.proxy_username,
                            password=self.proxy_password)
            self.force_use_proxy(settings)
            response = yield self.request(iri, method, extra_headers,
                                         oauth_credentials, post_content)
            defer.returnValue(response)

    @defer.inlineCallbacks
    def request(self, iri, method="GET", extra_headers=None,
                oauth_credentials=None, post_content=None):
        """Return a deferred that will be fired with a Response object."""
        uri = self.iri_to_uri(iri)
        headers = yield self.build_request_headers(uri, method, extra_headers,
                                                   oauth_credentials)
        d = defer.Deferred()
        message = self.soup.Message.new(method, uri)

        for key, value in headers.items():
            message.request_headers.append(key, value)

        if post_content:
            message.request_body.append(post_content)

        self.session.queue_message(message, self._on_message, d)
        d.addErrback(self._on_proxy_authenticate, iri, method, extra_headers,
                     oauth_credentials, post_content)
        response = yield d
        defer.returnValue(response)

    def force_use_proxy(self, settings):
        """Setup this webclient to use the given proxy settings."""
        # pylint: disable=W0511
        proxy_uri = self.get_proxy_uri(settings)
        self.session.set_property("proxy-uri", proxy_uri)

    def get_proxy_uri(self, settings):
        """Get a Soup.URI for the proxy, or None if disabled."""
        if "host" in settings and "port" in settings:
            template = URI_ANONYMOUS_TEMPLATE
            if "username" in settings and "password" in settings:
                template = URI_USERNAME_TEMPLATE
            uri = template.format(**settings)
            return self.soup.URI.new(uri)
        else:
            # If the proxy host is not set, use no proxy
            return None

    def shutdown(self):
        """End the soup session for this webclient."""
        self.session.abort()
