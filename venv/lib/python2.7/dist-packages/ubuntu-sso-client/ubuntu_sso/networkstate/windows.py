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
"""Network status implementation on Windows."""


# pylint: disable=F0401
# distutils-extra: ignore-import=pythoncom,win32com.server.policy
# distutils-extra: ignore-import=win32com.client
import pythoncom
# pylint: enable=F0401
from ctypes import windll, byref
from ctypes.wintypes import DWORD
from threading import Thread

from twisted.internet import defer
# pylint: disable=F0401
from win32com.server.policy import DesignatedWrapPolicy
from win32com.client import Dispatch
# pylint: enable=F0401

from ubuntu_sso.networkstate import NetworkFailException
from ubuntu_sso.networkstate.networkstates import ONLINE, OFFLINE
from ubuntu_sso.logger import setup_logging

logger = setup_logging("ubuntu_sso.networkstate")

# naming errors are deliberated because we are following the COM naming to make
# it clear for later developers.
# pylint: disable=C0103

## from EventSys.h
PROGID_EventSystem = "EventSystem.EventSystem"
PROGID_EventSubscription = "EventSystem.EventSubscription"

# SENS (System Event Notification Service) values for the events,
# this events contain the uuid of the event, the name of the event to be used
# as well as the method name of the method in the ISesNetwork interface that
# will be executed for the event.
# For more info look at:
# http://msdn.microsoft.com/en-us/library/aa377384(v=vs.85).aspx

SUBSCRIPTION_NETALIVE = ('{cd1dcbd6-a14d-4823-a0d2-8473afde360f}',
                         'UbuntuOne Network Alive',
                         'ConnectionMade')

SUBSCRIPTION_NETALIVE_NOQOC = ('{a82f0e80-1305-400c-ba56-375ae04264a1}',
                               'UbuntuOne Net Alive No Info',
                               'ConnectionMadeNoQOCInfo')

SUBSCRIPTION_NETLOST = ('{45233130-b6c3-44fb-a6af-487c47cee611}',
                        'UbuntuOne Network Lost',
                        'ConnectionLost')

SUBSCRIPTION_REACH = ('{4c6b2afa-3235-4185-8558-57a7a922ac7b}',
                       'UbuntuOne Network Reach',
                       'ConnectionMade')

SUBSCRIPTION_REACH_NOQOC = ('{db62fa23-4c3e-47a3-aef2-b843016177cf}',
                            'UbuntuOne Network Reach No Info',
                            'ConnectionMadeNoQOCInfo')

SUBSCRIPTION_REACH_NOQOC2 = ('{d4d8097a-60c6-440d-a6da-918b619ae4b7}',
                             'UbuntuOne Network Reach No Info 2',
                             'ConnectionMadeNoQOCInfo')

SUBSCRIPTIONS = [SUBSCRIPTION_NETALIVE,
                 SUBSCRIPTION_NETALIVE_NOQOC,
                 SUBSCRIPTION_NETLOST,
                 SUBSCRIPTION_REACH,
                 SUBSCRIPTION_REACH_NOQOC,
                 SUBSCRIPTION_REACH_NOQOC2]

SENSGUID_EVENTCLASS_NETWORK = '{d5978620-5b9f-11d1-8dd2-00aa004abd5e}'
SENSGUID_PUBLISHER = "{5fee1bd6-5b9b-11d1-8dd2-00aa004abd5e}"

# uuid of the implemented com interface
IID_ISesNetwork = '{d597bab1-5b9f-11d1-8dd2-00aa004abd5e}'


class NetworkManager(DesignatedWrapPolicy):
    """Implement ISesNetwork to know about the network status."""

    _com_interfaces_ = [IID_ISesNetwork]
    _public_methods_ = ['ConnectionMade',
                        'ConnectionMadeNoQOCInfo',
                        'ConnectionLost']
    _reg_clsid_ = '{41B032DA-86B5-4907-A7F7-958E59333010}'
    _reg_progid_ = "UbuntuOne.NetworkManager"

    def __init__(self, connected_cb=None, connected_cb_info=None,
                 disconnected_cb=None):
        # pylint: disable=E1101,E1120,W0231
        self._wrap_(self)
        # pylint: enable=E1101,E1120
        self.connected_cb = connected_cb
        self.connected_cb_info = connected_cb_info
        self.disconnected_cb = disconnected_cb

    def ConnectionMade(self, *args):
        """Tell that the connection is up again."""
        logger.info('Connection was made.')
        if self.connected_cb_info:
            self.connected_cb_info()

    def ConnectionMadeNoQOCInfo(self, *args):
        """Tell that the connection is up again."""
        logger.info('Connection was made no info.')
        if self.connected_cb:
            self.connected_cb()

    def ConnectionLost(self, *args):
        """Tell the connection was lost."""
        logger.info('Connection was lost.')
        if self.disconnected_cb:
            self.disconnected_cb()

    def register(self):
        """Register to listen to network events."""
        # call the CoInitialize to allow the registration to run in another
        # thread
        # pylint: disable=E1101
        pythoncom.CoInitialize()
        # interface to be used by com
        manager_interface = pythoncom.WrapObject(self)
        event_system = Dispatch(PROGID_EventSystem)
        # register to listen to each of the events to make sure that
        # the code will work on all platforms.
        for current_event in SUBSCRIPTIONS:
            # create an event subscription and add it to the event
            # service
            event_subscription = Dispatch(PROGID_EventSubscription)
            event_subscription.EventClassId = SENSGUID_EVENTCLASS_NETWORK
            event_subscription.PublisherID = SENSGUID_PUBLISHER
            event_subscription.SubscriptionID = current_event[0]
            event_subscription.SubscriptionName = current_event[1]
            event_subscription.MethodName = current_event[2]
            event_subscription.SubscriberInterface = manager_interface
            event_subscription.PerUser = True
            # store the event
            try:
                event_system.Store(PROGID_EventSubscription,
                                   event_subscription)
            except pythoncom.com_error as e:
                logger.error(
                    'Error registering %s to event %s', e, current_event[1])

        pythoncom.PumpMessages()
        # pylint: enable=E1101


def is_machine_connected():
    """Return a deferred that when fired, returns if the machine is online."""
    # pylint: disable=W0703, W0702
    try:
        wininet = windll.wininet
        flags = DWORD()
        connected = wininet.InternetGetConnectedState(byref(flags), None)
        return defer.succeed(connected == 1)
    except Exception as e:
        logger.exception('is_machine_connected failed with:')
        return defer.fail(NetworkFailException(e))
    # pylint: enable=W0703, W0702


class NetworkManagerState(object):
    """Check for status changed in the network on Windows."""

    def __init__(self, result_cb, **kwargs):
        """Initialize this instance with a result and error callbacks."""
        self.result_cb = result_cb

    def connection_made(self):
        """Return the connection state over the call back."""
        self.result_cb(ONLINE)

    def connection_lost(self):
        """Return the connection was lost over the call back."""
        self.result_cb(OFFLINE)

    def find_online_state(self, listener=None, listener_thread=None):
        """Get the network state and return it thru the set callback."""
        # check the current status right now
        if is_machine_connected():
            self.result_cb(ONLINE)
        else:
            self.result_cb(OFFLINE)
        if listener is None:
            # start listening for network changes
            listener = NetworkManager(connected_cb=self.connection_made,
                                      disconnected_cb=self.connection_lost)
        if listener_thread is None:
            listener_thread = Thread(target=listener.register,
                                     name='Ubuntu SSO NetworkManager')
        listener_thread.daemon = True
        listener_thread.start()
