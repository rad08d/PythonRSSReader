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
"""Network state detection on OS X.

is_machine_connected(): (deferred) returns connected state as bool
NetworkManagerState: class with listening thread, calls back with state changes
"""

from twisted.internet import defer

from threading import Thread

from ubuntu_sso.networkstate import NetworkFailException
from ubuntu_sso.networkstate.networkstates import (ONLINE, OFFLINE, UNKNOWN)
from ubuntu_sso.logger import setup_logging
logger = setup_logging("ubuntu_sso.networkstate")

HOSTNAME_TO_CHECK = 'one.ubuntu.com'

from ctypes import (
    CDLL,
    POINTER,
    CFUNCTYPE,
    Structure,
    pointer,
    c_bool,
    c_long,
    c_void_p,
    c_uint32)

from ctypes.util import find_library

# pylint: disable=C0103

# Functions and constants below are from
# /System/Library/CoreFoundation.framework/
CoreFoundationPath = find_library("CoreFoundation")
CoreFoundation = CDLL(CoreFoundationPath)

# CFRunLoopRef CFRunLoopGetCurrent()
CFRunLoopGetCurrent = CoreFoundation.CFRunLoopGetCurrent
CFRunLoopGetCurrent.restype = c_void_p
CFRunLoopGetCurrent.argtypes = []

# void CFRelease(CFTypeRef)
CFRelease = CoreFoundation.CFRelease
CFRelease.restype = None
CFRelease.argtypes = [c_void_p]

# void CFRunLoopRun()
CFRunLoopRun = CoreFoundation.CFRunLoopRun

# const CFStringRef kCFRunLoopDefaultMode
# pylint: disable=E1101
kCFRunLoopDefaultMode = c_void_p.in_dll(CoreFoundation,
                                        "kCFRunLoopDefaultMode")


# Functions and constants below are from
# /System/Library/SystemConfiguration.framework/
SystemConfigurationPath = find_library("SystemConfiguration")

# SystemConfiguration abbreviated as "SC" below:
SC = CDLL(SystemConfigurationPath)

# "SCNetworkReachability" functions abbreviated to "SCNR*" here.

# SCNetworkReachabilityRef
# SCNetworkReachabilityCreateWithName(CFAllocatorRef, const char *)
SCNRCreateWithName = SC.SCNetworkReachabilityCreateWithName
SCNRCreateWithName.restype = c_void_p

# Boolean SCNetworkReachabilityGetFlags(SCNetworkReachabilityRef,
#                                       SCNetworkReachabilityFlags)
SCNRGetFlags = SC.SCNetworkReachabilityGetFlags
SCNRGetFlags.restype = c_bool
SCNRGetFlags.argtypes = [c_void_p,
                         POINTER(c_uint32)]

SCNRScheduleWithRunLoop = SC.SCNetworkReachabilityScheduleWithRunLoop
SCNRScheduleWithRunLoop.restype = c_bool
SCNRScheduleWithRunLoop.argtypes = [c_void_p,
                                    c_void_p,
                                    c_void_p]

# ctypes callback type to match SCNetworkReachabilityCallback
# void (*SCNetworkReachabilityCallback) (SCNetworkReachabilityRef,
#                                        SCNetworkReachabilityFlags,
#                                        void *)
SCNRCallbackType = CFUNCTYPE(None, c_void_p, c_uint32, c_void_p)
# NOTE: need to keep this reference alive as long as a callback might occur.

# Boolean SCNetworkReachabilitySetCallback(SCNetworkReachabilityRef,
#                                          SCNetworkReachabilityCallback,
#                                          SCNetworkReachabilityContext)
SCNRSetCallback = SC.SCNetworkReachabilitySetCallback
SCNRSetCallback.restype = c_bool
SCNRSetCallback.argtypes = [c_void_p,
                            SCNRCallbackType,
                            c_void_p]
# pylint: enable=E1101


def check_connected_state():
    """Calls Synchronous SCNR API, returns bool."""
    target = SCNRCreateWithName(None, HOSTNAME_TO_CHECK)
    if target is None:
        logger.error("Error creating network reachability reference.")
        raise NetworkFailException()

    flags = c_uint32(0)
    ok = SCNRGetFlags(target, pointer(flags))
    CFRelease(target)

    if not ok:
        logger.error("Error getting reachability status of '%s'" %
                     HOSTNAME_TO_CHECK)
        raise NetworkFailException()

    return flags_say_reachable(flags.value)


def flags_say_reachable(flags):
    """Check flags returned from SCNetworkReachability API. Returns bool.

    Requires some logic:
    reachable_flag isn't enough on its own.

    A down wifi will return flags = 7, or reachable_flag and
    connection_required_flag, meaning that the host *would be*
    reachable, but you need a connection first.  (And then you'd
    presumably be best off checking again.)
    """
    # values from SCNetworkReachability.h
    reachable_flag = 1 << 1
    connection_required_flag = 1 << 2

    if flags & connection_required_flag:
        return False
    elif flags & reachable_flag:
        return True
    else:
        return False


class SCNRContext(Structure):

    """A struct to send as SCNetworkReachabilityContext to SCNRSetCallback.

    We don't use the fields currently.
    """

    _fields_ = [("version", c_long),
                ("info", c_void_p),
                ("retain", c_void_p),           # func ptr
                ("release", c_void_p),          # func ptr
                ("copyDescription", c_void_p)]  # func ptr


class NetworkManagerState(object):

    """Probe Network State and receive callbacks on changes.

    This class uses both synchronous and async API from the
    SystemConfiguration framework.

    To use: Initialize with a callback function, then call
    find_online_state. The callback will be called once immediately
    with the current state and then only on state changes.

    Any exceptions in checking state will result in the callback being
    called with UNKNOWN. At this point the listening thread is no
    longer runing, and a new NetworkManagerState should be created.

    NOTE: the callback will be called from the separate listening
    thread, except for the first call.
    """

    def __init__(self, result_cb):
        """Initialize and save result callback function.

        result_cb should take one argument, a networkstate object.

        The callback will be called with one of ONLINE, OFFLINE, or
        UNKNOWN, as defined in networkstates.py.
        """
        self.result_cb = result_cb
        self.listener_thread = None

    def _state_changed(self, flags):
        """Testable callback called by reachability_state_changed_cb.

        Used because reachability_state_changed_cb has to have a
        particular method signature.

        Clients should not call this method.
        """
        if flags_say_reachable(flags):
            self.result_cb(ONLINE)
        else:
            self.result_cb(OFFLINE)

    def _listen_on_separate_thread(self):
        """In separate thread, setup callback and listen for changes.

        On error, calls result_cb(UNKNOWN) and returns.
        """

        def reachability_state_changed_cb(targetref, flags, info):
            """Callback for SCNetworkReachability API

            This callback is passed to the SCNetworkReachability API,
            so its method signature has to be exactly this. Therefore,
            we declare it here and just call _state_changed with
            flags."""
            self._state_changed(flags)

        c_callback = SCNRCallbackType(reachability_state_changed_cb)
        context = SCNRContext(0, None, None, None, None)

        target = SCNRCreateWithName(None, HOSTNAME_TO_CHECK)
        if target is None:
            logger.error("Error creating SCNetworkReachability target")
            self.result_cb(UNKNOWN)
            return

        ok = SCNRSetCallback(target, c_callback, pointer(context))
        if not ok:
            logger.error("error setting SCNetworkReachability callback")
            CFRelease(target)
            self.result_cb(UNKNOWN)
            return

        ok = SCNRScheduleWithRunLoop(target,
                                     CFRunLoopGetCurrent(),
                                     kCFRunLoopDefaultMode)
        if not ok:
            logger.error("error scheduling on runloop: SCNetworkReachability")
            CFRelease(target)
            self.result_cb(UNKNOWN)
            return

        CFRunLoopRun()

        CFRelease(target)               # won't happen

    def _start_listening_thread(self):
        """Start the separate listener thread.

        Currently will not start one more than once.
        Should be OK because we don't expect errors the listen method.

        To add more error handling support, you could either add a
        call to join and re-start, or client could just create a new
        NetworkManagerState.
        """

        if self.listener_thread is None:
            self.listener_thread = Thread(
                target=self._listen_on_separate_thread,
                name="Ubuntu SSO Network Connection Monitor")
            self.listener_thread.daemon = True
            self.listener_thread.start()

    def find_online_state(self):
        """Calls callback with current state. Starts listening thread."""
        try:
            if check_connected_state():
                self.result_cb(ONLINE)
            else:
                self.result_cb(OFFLINE)

        except Exception:               # pylint: disable=W0703
            logger.exception("Getting state from SCNetworkReachability")
            self.result_cb(UNKNOWN)
            return                      # don't start thread on error

        self._start_listening_thread()


def is_machine_connected():
    """Return a deferred that when fired, returns online state as a bool.

    Raises NetworkFailException for errors.
    """
    try:
        return defer.succeed(check_connected_state())
    except Exception as e:                # pylint: disable=W0703
        logger.exception("Exception calling check_connected_state:")
        return defer.fail(NetworkFailException(e))
