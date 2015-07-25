# -*- coding: utf-8 -*-
# Copyright 2010-2012 Canonical Ltd.  This software is licensed under the
# GNU Lesser General Public License version 3 (see the file LICENSE).

"""Classes for adding authentication headers to your API requests.

You usually want to pass in an instance of one of these classes when you
instantiate a ``PistonAPI`` object.
"""

import base64


def _unicodeify(s):
    if isinstance(s, bytes):
        return s.decode('utf-8')
    return s


class OAuthAuthorizer(object):
    """Authenticate to OAuth protected APIs."""
    def __init__(self, token_key, token_secret, consumer_key, consumer_secret,
                 oauth_realm="OAuth"):
        """Initialize a ``OAuthAuthorizer``.

        ``token_key``, ``token_secret``, ``consumer_key`` and
        ``consumer_secret`` are required for signing OAuth requests.  The
        ``oauth_realm`` to use is optional.
        """
        # 2012-11-19 BAW: python-oauthlib requires unicodes for its tokens and
        # secrets.  Assume utf-8 values.
        # https://github.com/idan/oauthlib/issues/68
        self.token_key = _unicodeify(token_key)
        self.token_secret = _unicodeify(token_secret)
        self.consumer_key = _unicodeify(consumer_key)
        self.consumer_secret = _unicodeify(consumer_secret)
        self.oauth_realm = oauth_realm

    def sign_request(self, url, method, body, headers):
        """Sign a request with OAuth credentials."""
        # 2012-11-19 BAW: In order to preserve API backward compatibility,
        # convert empty string body to None.  The old python-oauth library
        # would treat the empty string as "no body", but python-oauthlib
        # requires None.
        if not body:
            content_type = headers.get('Content-Type')
            if content_type == 'application/x-www-form-urlencoded':
                body = ''
            else:
                body = None
        # Import oauthlib here so that you don't need it if you're not going
        # to use it.  Plan B: move this out into a separate oauth module.
        from oauthlib.oauth1 import Client
        from oauthlib.oauth1.rfc5849 import SIGNATURE_PLAINTEXT
        oauth_client = Client(self.consumer_key, self.consumer_secret,
                              self.token_key, self.token_secret,
                              signature_method=SIGNATURE_PLAINTEXT,
                              realm=self.oauth_realm)
        uri, signed_headers, body = oauth_client.sign(
            url, method, body, headers)
        headers.update(signed_headers)


class BasicAuthorizer(object):
    """Authenticate to Basic protected APIs."""
    def __init__(self, username, password):
        """Initialize a ``BasicAuthorizer``.

        You'll need to provide the ``username`` and ``password`` that will
        be used to authenticate with the server.
        """
        self.username = username
        self.password = password

    def sign_request(self, url, method, body, headers):
        """Sign a request with Basic credentials."""
        headers['Authorization'] = self.auth_header()

    def auth_header(self):
        s = '%s:%s' % (self.username, self.password)
        encoded = base64.b64encode(s.encode('utf-8')).decode('utf-8')
        return 'Basic ' + encoded
