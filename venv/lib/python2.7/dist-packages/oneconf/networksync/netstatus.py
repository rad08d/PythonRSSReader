#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (C) 2011 Canonical
#
# Authors:
#   Matthew McGowan
#   Michael Vogt
#   Didier Roche
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


import dbus
from gi.repository import GObject, GLib
import logging
import os

LOG = logging.getLogger(__name__)


class NetworkStatusWatcher(GObject.GObject):
    """ simple watcher which notifys subscribers to network events..."""

    # enums for network manager status
    # Old enum values are for NM 0.7

    # The NetworkManager daemon is in an unknown state.
    NM_STATE_UNKNOWN            = 0
    NM_STATE_UNKNOWN_LIST       = [NM_STATE_UNKNOWN]
    # The NetworkManager daemon is asleep and all interfaces managed by it are inactive.
    NM_STATE_ASLEEP_OLD         = 1
    NM_STATE_ASLEEP             = 10
    NM_STATE_ASLEEP_LIST        = [NM_STATE_ASLEEP_OLD,
                                   NM_STATE_ASLEEP]
    # The NetworkManager daemon is connecting a device.
    NM_STATE_CONNECTING_OLD     = 2
    NM_STATE_CONNECTING         = 40
    NM_STATE_CONNECTING_LIST    = [NM_STATE_CONNECTING_OLD,
                                   NM_STATE_CONNECTING]
    # The NetworkManager daemon is connected.
    NM_STATE_CONNECTED_OLD      = 3
    NM_STATE_CONNECTED_LOCAL    = 50
    NM_STATE_CONNECTED_SITE     = 60
    NM_STATE_CONNECTED_GLOBAL   = 70
    NM_STATE_CONNECTED_LIST     = [NM_STATE_CONNECTED_OLD,
                                   NM_STATE_CONNECTED_LOCAL,
                                   NM_STATE_CONNECTED_SITE,
                                   NM_STATE_CONNECTED_GLOBAL]
    # The NetworkManager daemon is disconnecting.
    NM_STATE_DISCONNECTING      = 30
    NM_STATE_DISCONNECTING_LIST = [NM_STATE_DISCONNECTING]
    # The NetworkManager daemon is disconnected.
    NM_STATE_DISCONNECTED_OLD   = 4
    NM_STATE_DISCONNECTED       = 20
    NM_STATE_DISCONNECTED_LIST  = [NM_STATE_DISCONNECTED_OLD,
                                   NM_STATE_DISCONNECTED]

    __gsignals__ = {'changed':(GObject.SIGNAL_RUN_FIRST,
                               GObject.TYPE_NONE,
                               (bool,)),
                   }

    def __init__(self):
        GObject.GObject.__init__(self)
        self.connected = False


        # check is ONECONF_NET_CONNECTED is in the environment variables
        # if so force the network status to be connected or disconnected
        if "ONECONF_NET_CONNECTED" in os.environ:
            if os.environ["ONECONF_NET_CONNECTED"].lower() == 'true':
                GLib.idle_add(self._on_connection_state_changed,
                              self.NM_STATE_CONNECTED_LOCAL)
                LOG.warn('forced netstate into connected mode...')
            else:
                GLib.idle_add(self._on_connection_state_changed,
                              self.NM_STATE_DISCONNECTED)
                LOG.warn('forced netstate into disconnected mode...')
            return
        try:
            bus = dbus.SystemBus()
            nm = bus.get_object('org.freedesktop.NetworkManager',
                                '/org/freedesktop/NetworkManager')
            nm.connect_to_signal("StateChanged", self._on_connection_state_changed)
            network_state = nm.state(dbus_interface='org.freedesktop.NetworkManager')
            self._on_connection_state_changed(network_state)

        except Exception as e:
            LOG.warn("failed to init network state watcher '%s'" % e)
            self._on_connection_state_changed(self.NM_STATE_UNKNOWN)


    def _on_connection_state_changed(self, state):
        LOG.debug("network status changed to %i", state)

        # this is to avoid transient state when we turn wifi on and nm tell
        # "is connected" by default until checking
        GLib.timeout_add_seconds(1, self._ensure_new_connected_state,
                                 self._does_state_mean_connected(state))

    def _ensure_new_connected_state(self, connected):
        '''check if the connectivity state changed since last check

        This is to avoid some transient state with nm flickering between connected and not connected'''
        if self.connected == connected:
            return

        self.connected = connected
        LOG.debug("Connectivity state changed to: %s", self.connected)
        self.emit("changed", self.connected)


    def _does_state_mean_connected(self, network_state):
        """ get bool if we the state means we are connected """

        # unkown because in doubt, just assume we have network
        return network_state in self.NM_STATE_UNKNOWN_LIST + self.NM_STATE_CONNECTED_LIST


if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG)

    from dbus.mainloop.glib import DBusGMainLoop
    DBusGMainLoop(set_as_default=True)
    network = NetworkStatusWatcher()
    loop = GObject.MainLoop()

    def print_state(new_network, connected):
        print("Connectivity state: %s" % connected)
    network.connect("changed", print_state)

    loop.run()
