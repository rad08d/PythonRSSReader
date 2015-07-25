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
"""tcpactivation: start a process if nothing listening in a given port."""

import subprocess

from twisted.internet import defer, error, protocol
from twisted.internet.endpoints import clientFromString

LOCALHOST = "127.0.0.1"
DELAY_BETWEEN_CHECKS = 0.1
NUMBER_OF_CHECKS = 600

# twisted uses a different coding convention
# pylint: disable=C0103,W0232


def async_sleep(delay):
    """Fire the returned deferred after some specified delay."""
    from twisted.internet import reactor
    d = defer.Deferred()
    # pylint: disable=E1101
    reactor.callLater(delay, d.callback, None)
    return d


class AlreadyStartedError(Exception):
    """The instance was already started."""


class ActivationTimeoutError(Exception):
    """Timeout while trying to start the instance."""


class NullProtocol(protocol.Protocol):
    """A protocol that drops the connection."""

    def connectionMade(self):
        """Just drop the connection."""
        self.transport.loseConnection()


class PortDetectFactory(protocol.ClientFactory):
    """Will detect if something is listening in a given port."""

    protocol = NullProtocol

    def __init__(self):
        """Initialize this instance."""
        self.d = defer.Deferred()

    def is_listening(self):
        """A deferred that will become True if something is listening."""
        return self.d

    def buildProtocol(self, addr):
        """Connected."""
        p = protocol.ClientFactory.buildProtocol(self, addr)
        if not self.d.called:
            self.d.callback(True)
        return p

    def clientConnectionLost(self, connector, reason):
        """The connection was lost."""
        protocol.ClientFactory.clientConnectionLost(self, connector, reason)
        if not self.d.called:
            self.d.callback(False)

    def clientConnectionFailed(self, connector, reason):
        """The connection failed."""
        protocol.ClientFactory.clientConnectionFailed(self, connector, reason)
        if not self.d.called:
            self.d.callback(False)


class ActivationConfig(object):
    """The configuration for tcp activation."""

    def __init__(self, service_name, command_line, description):
        """Initialize this instance."""
        self.service_name = service_name
        self.command_line = command_line
        self.description = description


class ActivationDetector(object):
    """Base class to detect if the service is running."""

    def __init__(self, config):
        """Initialize this instance."""
        self.config = config

    @defer.inlineCallbacks
    def is_already_running(self):
        """Check if the instance is already running."""
        from twisted.internet import reactor
        factory = PortDetectFactory()
        client = clientFromString(reactor, self.config.description.client)
        try:
            yield client.connect(factory)
        except error.ConnectError:
            defer.returnValue(False)
        result = yield factory.is_listening()
        defer.returnValue(result)


class ActivationClient(ActivationDetector):
    """A client for tcp activation."""

    # a classwide lock, so the server is started only once
    lock = defer.DeferredLock()

    @defer.inlineCallbacks
    def _wait_server_active(self):
        """Wait till the server is active."""
        for _ in range(NUMBER_OF_CHECKS):
            is_running = yield self.is_already_running()
            if is_running:
                defer.returnValue(None)
            yield async_sleep(DELAY_BETWEEN_CHECKS)
        raise ActivationTimeoutError()

    def _spawn_server(self):
        """Start running the server process."""
        # Without using close_fds=True, strange things happen
        # with logging on windows. More information at
        # http://bugs.python.org/issue4749
        subprocess.Popen(self.config.command_line, close_fds=True)

    @defer.inlineCallbacks
    def _do_get_active_description(self):
        """Get the details for the running instance, starting it if needed."""
        is_running = yield self.is_already_running()
        if not is_running:
            self._spawn_server()
            yield self._wait_server_active()
        defer.returnValue(self.config.description.client)

    @defer.inlineCallbacks
    def get_active_client_description(self):
        """Serialize the requests to _do_get_active_description."""
        yield self.lock.acquire()
        try:
            result = yield self._do_get_active_description()
            defer.returnValue(result)
        finally:
            self.lock.release()


class ActivationInstance(ActivationDetector):
    """A tcp activation server instance."""

    @defer.inlineCallbacks
    def get_server_description(self):
        """Get the port to run this service or fail if already started."""
        is_running = yield self.is_already_running()
        if is_running:
            raise AlreadyStartedError()
        defer.returnValue(self.config.description.server)
