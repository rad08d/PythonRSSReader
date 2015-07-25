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
"""Perspective Broker IPC utils."""

from functools import wraps, partial
from collections import defaultdict

from twisted.internet import defer, endpoints
from twisted.spread.pb import (
    DeadReferenceError,
    NoSuchMethod,
    PBClientFactory,
    PBServerFactory,
    Referenceable,
    Root,
)

from ubuntu_sso.logger import setup_logging
from ubuntu_sso.utils.tcpactivation import (
    ActivationClient,
    ActivationConfig,
    ActivationInstance,
)


logger = setup_logging("ubuntu_sso.utils.ipc")
LOCALHOST = '127.0.0.1'

# pylint: disable=E1103


@defer.inlineCallbacks
def server_listen(server_factory, service_name, activation_cmdline,
                  description, reactor=None):
    """Connect the IPC server factory."""
    config = ActivationConfig(service_name, activation_cmdline, description)
    ai = ActivationInstance(config)
    description = yield ai.get_server_description()

    if reactor is None:
        from twisted.internet import reactor
    server = endpoints.serverFromString(reactor, description)
    connector = yield server.listen(server_factory)
    defer.returnValue(connector)


@defer.inlineCallbacks
def client_connect(client_factory, service_name, activation_cmdline,
                   description, reactor=None):
    """Connect the IPC client factory."""
    config = ActivationConfig(service_name, activation_cmdline, description)
    ac = ActivationClient(config)
    description = yield ac.get_active_client_description()

    if reactor is None:
        from twisted.internet import reactor

    client = endpoints.clientFromString(reactor, description)
    port = yield client.connect(client_factory)
    defer.returnValue(port)


# pylint: enable=E1103

# ============================== service helpers ==============================

def signal(f):
    """Decorator to emit a signal."""

    @wraps(f)
    def inner(self, *args, **kwargs):
        """Grab the signal name from the internal mapping and emit."""
        f(self, *args, **kwargs)
        signal_name = f.__name__
        self.emit_signal(signal_name, *args, **kwargs)

    return inner


class SignalBroadcaster(object):
    """Object that allows to emit signals to clients over the IPC."""

    MSG_NO_SIGNAL_HANDLER = "No signal handler for %r in %r"
    MSG_COULD_NOT_EMIT_SIGNAL = "Could not emit signal %r to %r due to %r"

    def __init__(self):
        """Create a new instance."""
        super(SignalBroadcaster, self).__init__()
        self.clients_per_signal = defaultdict(set)

    def _ignore_no_such_method(self, failure, signal_name, current_client):
        """NoSuchMethod is not an error, ignore it."""
        failure.trap(NoSuchMethod)
        logger.debug(self.MSG_NO_SIGNAL_HANDLER, signal_name, current_client)

    def _other_failure(self, failure, signal_name, current_client):
        """Log the issue when emitting a signal."""
        logger.warning(self.MSG_COULD_NOT_EMIT_SIGNAL, signal_name,
                       current_client, failure.value)
        logger.warning('Traceback is:\n%s', failure.printDetailedTraceback())

    def remote_register_to_signals(self, client, signals):
        """Allow a client to register to some signals."""
        for signal_name in signals:
            self.clients_per_signal[signal_name].add(client)

    def remote_unregister_to_signals(self, client):
        """Allow a client to unregister from the signal."""
        for connected_clients in self.clients_per_signal.values():
            if client in connected_clients:
                connected_clients.remove(client)

    def emit_signal(self, signal_name, *args, **kwargs):
        """Emit the given signal to the clients."""
        logger.debug("emitting %r to all (%i) connected clients.",
                     signal_name, len(self.clients_per_signal[signal_name]))
        result = []
        dead_clients = set()
        for current_client in self.clients_per_signal[signal_name]:
            try:
                d = current_client.callRemote(signal_name, *args, **kwargs)
                d.addErrback(self._ignore_no_such_method, signal_name,
                                                          current_client)
                d.addErrback(self._other_failure, signal_name, current_client)
                result.append(d)
            except DeadReferenceError:
                dead_clients.add(current_client)
        for client in dead_clients:
            logger.warn('emit_signal: Unregistering dead client %s.', client)
            self.remote_unregister_to_signals(client)


class RemoteMeta(type):
    """Append remote_ to the remote methods.

    Remote has to be appended to the remote method to work over pb but this
    names cannot be used since the other platforms do not expect the remote
    prefix. This metaclass creates those prefixes so that the methods can be
    correctly called.
    """

    def __new__(mcs, name, bases, attrs):
        remote_calls = attrs.get('remote_calls', [])
        for current in remote_calls:
            attrs['remote_' + current] = attrs[current]
        return super(RemoteMeta, mcs).__new__(mcs, name, bases, attrs)


def meta_base(meta):
    """A function to return a metaclass which is called directly.
    This is safe for both Python 2 and 3."""
    return meta("MetaBase", (object,), {})


class RemoteService(meta_base(RemoteMeta),
                    Referenceable, SignalBroadcaster):
    """A remote service that provides the methods listed in remote_calls."""

    remote_calls = []


class BaseService(object, Root):
    """Base PB service.

    Inherit from this class and define name, description and cmdline.

    If 'start' is called, 'shutdown' should be called when done.

    """

    # a mapping of (service name, service class (an instance of RemoteService))
    services = {}
    name = None
    description = None
    cmdline = None

    def __init__(self, *a, **kw):
        super(BaseService, self).__init__()
        self.factory = None
        self.listener = None
        for name, service_class in self.services.items():
            service = service_class(*a, **kw)
            setattr(self, name, service)
            setattr(self, 'remote_get_%s' % name,
                    partial(self._get_service, name))

    def _get_service(self, name):
        """Return the instance of the service named 'name'."""
        return getattr(self, name)

    @defer.inlineCallbacks
    def start(self):
        """Start listening in the proper description."""
        self.factory = PBServerFactory(self)
        self.listener = yield server_listen(self.factory,
                                            self.name,
                                            self.cmdline,
                                            self.description)

    def shutdown(self):
        """Stop listening."""
        self.listener.stopListening()


# ============================== client helpers ==============================


class RemoteClient(object, Referenceable):
    """Represent a client for remote calls."""

    call_remote_functions = []  # methods that can be called on the remote obj
    signal_handlers = []  # signals that are of interest of this client

    def __init__(self, base_client, remote_object):
        """Create instance."""
        super(RemoteClient, self).__init__()
        self._mapping = defaultdict(list)
        self.base_client = base_client
        self.remote = remote_object

        # for each function name in self.call_remote_functions,
        # set as instance attribute a function that will execute
        # self.remote.callRemote(function name, *a, **kw)
        for name in self.call_remote_functions:
            setattr(self, name, partial(self.call_method, name))

        # for each signal name in self.signal_handlers,
        # set as instance attribute a function that will execute
        # all the callbacks registered with connect_to_signal, plus
        # the method self.<signal_name>_cb(*a, **kw) if defined
        for name in self.signal_handlers:
            setattr(self, 'remote_' + name, self._emit_signal(name))

    def _emit_signal(self, fname):
        """Return a function that will execute the 'fname' method."""

        def callback_wrapper(*args, **kwargs):
            """Return the result of the callback if present."""
            for callback in self._mapping[fname]:
                logger.info('Emitting remote signal for %s with callback %r.',
                            fname, callback)
                callback(*args, **kwargs)

            # execute methods ending with _cb as signal handlers,
            # only for old compatibility
            old_name = ['on']
            for i in fname:
                if i.isupper():
                    old_name.append('_' + i.lower())
                else:
                    old_name.append(i)
            old_name.append('_cb')

            callback = getattr(self, ''.join(old_name), None)
            if callback is not None:
                logger.info('Emitting remote signal for %s with callback %r.',
                            fname, callback)
                callback(*args, **kwargs)

        return callback_wrapper

    @defer.inlineCallbacks
    def call_method(self, method_name, *args, **kwargs):
        """Call asynchronously 'method_name(*args)'.

        Return a deferred that will be fired when the call finishes.
        For now, **kwargs are ignored.

        """
        logger.debug('Performing %r as a remote call (%r, %r).',
                     method_name, args, kwargs)
        try:
            result = yield self.remote.callRemote(method_name, *args)
        except DeadReferenceError:
            yield self.base_client.reconnect()
            result = yield self.call_method(method_name, *args, **kwargs)
        defer.returnValue(result)

    @defer.inlineCallbacks
    def register_to_signals(self):
        """Register to the signals."""
        try:
            result = yield self.remote.callRemote('register_to_signals', self,
                    self.signal_handlers)
        except DeadReferenceError:
            yield self.base_client.reconnect()
            result = yield self.register_to_signals()
        defer.returnValue(result)

    def unregister_to_signals(self):
        """Register to the signals."""
        return self.remote.callRemote('unregister_to_signals', self)

    def connect_to_signal(self, signal_name, callback):
        """Register 'callback' to be called when 'signal_name' is emitted."""
        self._mapping[signal_name].append(callback)
        return callback

    def disconnect_from_signal(self, signal_name, match):
        """Unregister 'match' from 'signal_name'.

        'match' is the object returned by 'connect_to_signal'.

        """
        if match in self._mapping[signal_name]:
            self._mapping[signal_name].remove(match)


class BaseClient(object):
    """Client that will connect to the service listening on the description.

    Inherit from this class and define service_name, service_description and
    service_cmdline so they return the proper values.

    The service_cmdline must be redefined so it returns the command line to
    execute to run the service, if it's not running.

    If 'connect' is called, 'disconnect' should be called when done.

    """

    # a mapping of (client name, client class (an instance of RemoteClient))
    clients = {}
    service_name = None
    service_description = None
    service_cmdline = None

    def __init__(self):
        self.factory = None
        self.client = None
        for client in self.clients:
            setattr(self, client, None)

    @defer.inlineCallbacks
    def _request_remote_objects(self, root):
        """Request all the diff remote objects used for the communication."""
        logger.debug('Requesting remote objects (%r) for %s',
                     self.clients.keys(), self.__class__.__name__)
        for name, client_class in self.clients.items():
            remote = yield root.callRemote('get_%s' % name)
            setattr(self, name, client_class(self, remote))

    @defer.inlineCallbacks
    def connect(self):
        """Connect to the remote service."""
        self.factory = PBClientFactory()
        self.client = yield client_connect(self.factory,
                                           self.service_name,
                                           self.service_cmdline,
                                           self.service_description)
        root = yield self.factory.getRootObject()
        yield self._request_remote_objects(root)
        yield self.register_to_signals()

    @defer.inlineCallbacks
    def reconnect(self):
        """Reconnect with the server."""
        self.factory = PBClientFactory()
        self.client = yield client_connect(self.factory,
                                           self.service_name,
                                           self.service_cmdline,
                                           self.service_description)
        root = yield self.factory.getRootObject()
        # loop over the already present remote clients and reset their remotes
        for name in self.clients:
            remote = yield root.callRemote('get_%s' % name)
            remote_client = getattr(self, name)
            remote_client.remote = remote
        yield self.register_to_signals()

    @defer.inlineCallbacks
    def register_to_signals(self):
        """Register all the clients to their signals."""
        for name in self.clients:
            client = getattr(self, name)
            yield client.register_to_signals()

    @defer.inlineCallbacks
    def unregister_to_signals(self):
        """Unregister from the all the client's signals."""
        for name in self.clients:
            client = getattr(self, name)
            yield client.unregister_to_signals()

    @defer.inlineCallbacks
    def disconnect(self):
        """Disconnect from the process."""
        yield self.unregister_to_signals()
        if self.client:
            self.client.disconnect()
