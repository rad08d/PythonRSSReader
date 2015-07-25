# -*- coding: utf-8 -*-
#
# Copyright 2010-2012 Canonical Ltd.
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
"""Implementation of network state detection."""

import dbus

from twisted.internet import defer

from ubuntu_sso.networkstate import NetworkFailException
from ubuntu_sso.networkstate.networkstates import (
    ONLINE, OFFLINE,
    NM_STATE_CONNECTING_LIST,
    NM_STATE_CONNECTED_LIST,
    NM_STATE_DISCONNECTED_LIST,
)
from ubuntu_sso.logger import setup_logging
logger = setup_logging("ubuntu_sso.networkstate")

NM_DBUS_INTERFACE = "org.freedesktop.NetworkManager"
NM_DBUS_OBJECTPATH = "/org/freedesktop/NetworkManager"


class NetworkManagerState(object):
    """Checks the state of NetworkManager thru DBus."""

    def __init__(self, result_cb, dbus_module=dbus):
        """Initialize this instance with a result and error callbacks."""
        self.result_cb = result_cb
        self.dbus = dbus_module
        self.state_signal = None

    def call_result_cb(self, state):
        """Return the state thru the result callback."""
        self.result_cb(state)

    def got_state(self, state):
        """Called by DBus when the state is retrieved from NM."""
        if state in NM_STATE_CONNECTED_LIST:
            self.call_result_cb(ONLINE)
        elif state in NM_STATE_CONNECTING_LIST:
            logger.debug("Currently connecting, waiting for signal")
        else:
            self.call_result_cb(OFFLINE)

    def got_error(self, error):
        """Called by DBus when the state is retrieved from NM."""
        # Assuming since Network Manager is not running,
        # the user has connected in some other way
        logger.error("Error contacting NetworkManager: %s" %
                         str(error))
        self.call_result_cb(ONLINE)

    def state_changed(self, state):
        """Called when a signal is emmited by Network Manager."""
        if int(state) in NM_STATE_CONNECTED_LIST:
            self.call_result_cb(ONLINE)
        elif int(state) in NM_STATE_DISCONNECTED_LIST:
            self.call_result_cb(OFFLINE)
        else:
            logger.debug("Not yet connected: continuing to wait")

    def find_online_state(self):
        """Get the network state and return it thru the set callback."""
        try:
            sysbus = self.dbus.SystemBus()
            nm_proxy = sysbus.get_object(NM_DBUS_INTERFACE,
                                         NM_DBUS_OBJECTPATH,
                                         follow_name_owner_changes=True)
            nm_if = self.dbus.Interface(nm_proxy, NM_DBUS_INTERFACE)
            self.state_signal = nm_if.connect_to_signal(
                        signal_name="StateChanged",
                        handler_function=self.state_changed,
                        dbus_interface=NM_DBUS_INTERFACE)
            nm_proxy.Get(NM_DBUS_INTERFACE, "State",
                         reply_handler=self.got_state,
                         error_handler=self.got_error)
        except Exception as e:
            self.got_error(e)


def is_machine_connected():
    """Return a deferred that when fired, returns if the machine is online."""
    d = defer.Deferred()

    def got_state(state):
        """The state was retrieved from the Network Manager."""
        if type(state) is not type(ONLINE):
            logger.exception("bad callback argument in is_machine_connected")
            raise NetworkFailException()
        result = (state == ONLINE)
        d.callback(result)

    try:
        network = NetworkManagerState(got_state)
        network.find_online_state()
    except Exception as e:
        logger.exception('is_machine_connected failed with:')
        d.errback(NetworkFailException(e))

    return d
