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
"""Timestamp synchronization with the server."""

import time

from twisted.internet import defer

from ubuntu_sso import SSO_UONE_BASE_URL
from ubuntu_sso.logger import setup_logging

logger = setup_logging("ubuntu_sso.utils.webclient.timestamp")
NOCACHE_HEADERS = {"Cache-Control": "no-cache"}


class TimestampChecker(object):
    """A timestamp that's regularly checked with a server."""

    CHECKING_INTERVAL = 60 * 60  # in seconds
    ERROR_INTERVAL = 30  # in seconds
    SERVER_IRI = u"%s/api/time" % SSO_UONE_BASE_URL

    def __init__(self, webclient_class):
        """Initialize this instance."""
        self.next_check = time.time()
        self.skew = 0
        self.webclient_class = webclient_class

    @defer.inlineCallbacks
    def get_server_date_header(self, server_iri):
        """Get the server date using twisted webclient."""
        webclient = self.webclient_class()
        try:
            response = yield webclient.request(server_iri, method="HEAD",
                                               extra_headers=NOCACHE_HEADERS)
            defer.returnValue(response.headers["Date"][0])
        finally:
            webclient.shutdown()

    @defer.inlineCallbacks
    def get_server_time(self):
        """Get the time at the server."""
        date_string = yield self.get_server_date_header(self.SERVER_IRI)
        # delay import, otherwise a default reactor gets installed
        from twisted.web import http
        timestamp = http.stringToDatetime(date_string)
        defer.returnValue(timestamp)

    @defer.inlineCallbacks
    def get_faithful_time(self):
        """Get an accurate timestamp."""
        local_time = time.time()
        if local_time >= self.next_check:
            try:
                server_time = yield self.get_server_time()
                self.next_check = local_time + self.CHECKING_INTERVAL
                self.skew = server_time - local_time
                logger.debug("Calculated server time skew: %r", self.skew)
            # We just log all exceptions while trying to get the server time
            # pylint: disable=W0703
            except Exception as e:
                logger.debug("Error while verifying server time skew: %r", e)
                self.next_check = local_time + self.ERROR_INTERVAL
        # delay import, otherwise a default reactor gets installed
        from twisted.web import http
        logger.debug("Using corrected timestamp: %r",
                  http.datetimeToString(local_time + self.skew))
        defer.returnValue(int(local_time + self.skew))
