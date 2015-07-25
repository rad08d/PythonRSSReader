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
"""A webclient backend that uses twisted.web.client."""

import base64

try:
    # pylint: disable=E0611,F0401
    from urllib.parse import urlparse
    # pylint: enable=E0611,F0401
except ImportError:
    from urlparse import urlparse

from twisted.internet import defer

from ubuntu_sso.logger import setup_logging
from ubuntu_sso.utils.webclient.common import (
    BaseWebClient,
    HeaderDict,
    Response,
    UnauthorizedError,
    WebClientError,
)

logger = setup_logging("ubuntu_sso.utils.webclient.txweb")


class RawResponse(object):
    """A raw response from the webcall."""

    def __init__(self, headers, content, code=200, phrase="OK"):
        """Initialize this response."""
        self.headers = headers
        self.content = content
        self.code = code
        self.phrase = phrase


class WebClient(BaseWebClient):
    """A simple web client that does not support proxies, yet."""

    client_factory = None

    def __init__(self, connector=None, context_factory=None, **kwargs):
        """Initialize this webclient."""
        # delay import, otherwise a default reactor gets installed
        from twisted.web import client

        super(WebClient, self).__init__(**kwargs)

        if connector is None:
            from twisted.internet import reactor
            self.connector = reactor
        else:
            self.connector = connector

        if context_factory is None:
            from twisted.internet import ssl
            self.context_factory = ssl.ClientContextFactory()
        else:
            self.context_factory = context_factory

        # decide which client factory to use
        if WebClient.client_factory is None:
            self.client_factory = client.HTTPClientFactory
        else:
            self.client_factory = WebClient.client_factory

    @defer.inlineCallbacks
    def raw_request(self, method, uri, headers, postdata):
        """Make a raw http request."""
        # Twisted wants headers as bytes, but because of oauthlib, they might
        # be unicodes.  Assume utf-8 and revert the encodings.
        bytes_headers = {}
        for key, value in headers.items():
            if isinstance(key, unicode):
                key = key.encode('utf-8')
            if isinstance(value, unicode):
                value = value.encode('utf-8')
            bytes_headers[key] = value
        headers = bytes_headers

        # delay import, otherwise a default reactor gets installed
        from twisted.web import error

        parsed_url = urlparse(uri)

        # pylint: disable=E1101,E1103
        https = parsed_url.scheme == "https"
        host = parsed_url.netloc.split(":")[0]
        # pylint: enable=E1101,E1103
        if parsed_url.port is None:
            port = 443 if https else 80
        else:
            port = parsed_url.port

        factory = self.client_factory(uri, method=method,
                                       postdata=postdata,
                                       headers=headers,
                                       followRedirect=False)
        # pylint: disable=E1103
        if https:
            self.connector.connectSSL(host, port, factory,
                                      self.context_factory)
        else:
            self.connector.connectTCP(host, port, factory)
        # pylint: enable=E1103

        try:
            content = yield factory.deferred
            response = RawResponse(factory.response_headers, content)
        except error.Error as e:
            response = RawResponse(factory.response_headers, e.response,
                                   int(e.status), e.message)
        defer.returnValue(response)

    @defer.inlineCallbacks
    def request(self, iri, method="GET", extra_headers=None,
                oauth_credentials=None, post_content=None):
        """Get the page, or fail trying."""
        # delay import, otherwise a default reactor gets installed
        from twisted.web import http

        uri = self.iri_to_uri(iri)
        headers = yield self.build_request_headers(uri, method, extra_headers,
                                                   oauth_credentials)

        if self.username and self.password:
            auth = base64.b64encode(self.username + ":" + self.password)
            headers["Authorization"] = "Basic " + auth

        try:
            raw_response = yield self.raw_request(method, uri,
                                                  headers=headers,
                                                  postdata=post_content)
            response_headers = HeaderDict(raw_response.headers)
            if method.lower() != "head":
                response_content = raw_response.content
            else:
                response_content = ""
            if raw_response.code == http.OK:
                defer.returnValue(Response(response_content, response_headers))
            if raw_response.code == http.UNAUTHORIZED:
                raise UnauthorizedError(raw_response.phrase,
                                        response_content)
            raise WebClientError(raw_response.phrase, response_content)
        except WebClientError:
            raise
        except Exception as e:
            raise WebClientError(e.message, e)

    def force_use_proxy(self, settings):
        """Setup this webclient to use the given proxy settings."""
        # No direct proxy support in twisted.web.client
