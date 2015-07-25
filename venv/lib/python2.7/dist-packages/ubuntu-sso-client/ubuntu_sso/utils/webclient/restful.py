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
"""A proxy-enabled restful client."""

import json

try:
    # pylint: disable=E0611,F0401
    from urllib.parse import urlencode
    # pylint: enable=E0611,F0401
except ImportError:
    from urllib import urlencode

from twisted.internet import defer

from ubuntu_sso.logger import setup_logging
from ubuntu_sso.utils import webclient

logger = setup_logging("ubuntu_sso.utils.webclient.restful")

POST_HEADERS = {
    "content-type": "application/x-www-form-urlencoded",
}


class RestfulClient(object):
    """A proxy-enabled restful client."""

    def __init__(self, service_iri, username=None, password=None,
                 oauth_credentials=None):
        """Initialize this instance."""
        assert service_iri.endswith("/")
        self.service_iri = service_iri
        self.webclient = webclient.webclient_factory(username=username,
                                                     password=password,
                                                     oauth_sign_plain=True)
        self.oauth_credentials = oauth_credentials

    @defer.inlineCallbacks
    def restcall(self, method, **kwargs):
        """Make a restful call."""
        assert isinstance(method, unicode)
        params = {}
        for key, value in kwargs.items():
            if isinstance(value, basestring):
                assert isinstance(value, unicode)
            params[key] = json.dumps(value)
        namespace, operation = method.split(".")
        params["ws.op"] = operation
        encoded_args = urlencode(params)
        iri = self.service_iri + namespace
        creds = self.oauth_credentials
        logger.debug('Performing REST call to %r.', iri)
        result = yield self.webclient.request(iri, method="POST",
                                              oauth_credentials=creds,
                                              post_content=encoded_args,
                                              extra_headers=POST_HEADERS)
        try:
            response = json.loads(result.content)
        except:
            logger.exception('Can not load json from REST request response '
                             '(content is %r).', result.content)
            raise
        else:
            defer.returnValue(response)

    def shutdown(self):
        """Stop the webclient used by this class."""
        self.webclient.shutdown()
