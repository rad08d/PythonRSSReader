# -*- coding: utf-8 -*-
#
# Copyright 2012 Canonical Ltd.
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
"""Network states."""


class NetworkState(object):
    """ A simple class to add a label and make debugging easier. """

    def __init__(self, label="unlabeled"):
        self.label = label

    def __repr__(self):
        return "Network state (%s)" % self.label

# Values returned by the callback
(ONLINE, OFFLINE, UNKNOWN) = (NetworkState("online"),
                              NetworkState("offline"),
                              NetworkState("unknown"))

# Internal NetworkManager State constants
NM_STATE_UNKNOWN = 0
NM_STATE_UNKNOWN_LIST = [NM_STATE_UNKNOWN]
NM_STATE_ASLEEP_OLD = 1
NM_STATE_ASLEEP = 10
NM_STATE_ASLEEP_LIST = [NM_STATE_ASLEEP_OLD,
                        NM_STATE_ASLEEP]
NM_STATE_CONNECTING_OLD = 2
NM_STATE_CONNECTING = 40
NM_STATE_CONNECTING_LIST = [NM_STATE_CONNECTING_OLD,
                            NM_STATE_CONNECTING]
NM_STATE_CONNECTED_OLD = 3
NM_STATE_CONNECTED_LOCAL = 50
NM_STATE_CONNECTED_SITE = 60
NM_STATE_CONNECTED_GLOBAL = 70
# Specifically don't include local and site, as they won't let us get to server
NM_STATE_CONNECTED_LIST = [NM_STATE_CONNECTED_OLD,
                           NM_STATE_CONNECTED_GLOBAL]
NM_STATE_DISCONNECTED_OLD = 4
NM_STATE_DISCONNECTED = 20
# For us, local and site connections are the same as diconnected
NM_STATE_DISCONNECTED_LIST = [NM_STATE_DISCONNECTED_OLD,
                              NM_STATE_DISCONNECTED,
                              NM_STATE_CONNECTED_LOCAL,
                              NM_STATE_CONNECTED_SITE]
