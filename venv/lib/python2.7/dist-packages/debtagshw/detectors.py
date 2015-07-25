# detectors: lib to detect what hardware tags apply to the current system
#
# Copyright (C) 2012  Canonical
#
# Author:
#  Michael Vogt <mvo@ubuntu.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from __future__ import absolute_import

import logging
import os
import subprocess

LOG=logging.getLogger(__name__)

try:
    from gi.repository import GUdev
    HAVE_GUDEV = True
except ImportError:
    HAVE_GUDEV = False

from .enums import HardwareSupported
from . import opengl

class Detector(object):
    """ Base detector class """

    # helper functions for tags have this prefix, so the code can find them
    # via introspecton, e.g.
    # hardware::video:opengl -> _run_check_hardware__video_opengl
    CHECK_FUNCTION_PREFIX = "_run_check_"

    def is_supported(self, tag):
        """ check if the given tag is supported, returns a
            HardwareSupported class
        """
        f = self._get_func_for_tag(tag)
        if f:
            return f()
        return HardwareSupported.UNKNOWN

    def generate_tag_expressions(self):
        """ Generate debtags expressions for the given HW """
        for tag in self.get_supported_tags():
            res = self.is_supported(tag)
            if res == HardwareSupported.UNKNOWN:
                continue
            yield res, [tag]

    def get_supported_tags(self):
        """ return list of supported tags by this detector """
        supported = []
        for name in dir(self):
            tag = self._get_tag_for_func(name)
            if tag:
                supported.append(tag)
        return supported

    # private helpers
    def _has_func_for_tag(self, tag):
        return hasattr(self, "%s%s" % (
            self.CHECK_FUNCTION_PREFIX, tag.replace(":", "_")))

    def _get_func_for_tag(self, tag):
        return getattr(self, "%s%s" % (
            self.CHECK_FUNCTION_PREFIX, tag.replace(":", "_")), None)

    def _get_tag_for_func(self, func_name):
        if not func_name.startswith("%shardware" % self.CHECK_FUNCTION_PREFIX):
            return None
        tag = func_name[len(self.CHECK_FUNCTION_PREFIX):].replace("_",":")
        return tag


class DetectorUdev(Detector):
    """ detect hardware based on udev """

    DEBTAG_TO_UDEV_PROPERTY = {
        # storage
        "hardware::storage:cd" : "ID_CDROM",
        "hardware::storage:cd-writer" : "ID_CDROM_CD_R",
        "hardware::storage:dvd" : "ID_CDROM_DVD",
        "hardware::storage:dvd-writer" : "ID_CDROM_DVD_R",
        # input
        "hardware::input:touchscreen" : "ID_INPUT_TOUCH",
        "hardware::input:mouse" : "ID_INPUT_MOUSE",
        "hardware::input:keyboard" : "ID_INPUT_KEYBOARD",
        "hardware::input:joystick" : "ID_INPUT_JOYSTICK",
        # digicam
        "hardware::digicam" : "ID_GPHOTO2",
    }

    DEBTAG_TO_ID_TYPE = {
        # webcam
        'hardware::webcam' : 'video',
        # floppy
        'hardware::floppy' : 'floppy',
    }

    # all tags this class knows about
    SUPPORTED_TAGS = list(DEBTAG_TO_UDEV_PROPERTY.keys()) + \
                      list(DEBTAG_TO_ID_TYPE.keys())

    def __init__(self):
        if HAVE_GUDEV:
            self._uc = GUdev.Client()
        else:
            self._uc = None

    def is_supported(self, tag):
        LOG.debug("DetectorUdev.is_supported: '%s'" % tag)
        if self._uc is None:
            return HardwareSupported.UNKNOWN
        for device in self._uc.query_by_subsystem(None):
            #print device.get_property_keys(), device.get_property("DEVPATH")
            # supported a (theoretical at this point) udev property that
            # sets the debtag tag directly
            if device.has_property("HW_DEBTAGS"):
                return tag in device.get_property("HW_DEBTAGS")
            # use our own device detection magic
            prop = self.DEBTAG_TO_UDEV_PROPERTY.get(tag)
            if prop and device.has_property(prop):
                #print device.get_property(prop)
                if bool(device.get_property(prop)):
                    return HardwareSupported.YES
                else:
                    return HardwareSupported.NO
            # use ID_TYPE
            if device.has_property("ID_TYPE"):
                id_type = device.get_property("ID_TYPE")
                if (tag in self.DEBTAG_TO_ID_TYPE and
                    id_type == self.DEBTAG_TO_ID_TYPE[tag]):
                    return HardwareSupported.YES
        # if we know about the tag and did not find it, return NO
        # (LP: #1020057)
        if tag in self.SUPPORTED_TAGS:
            return HardwareSupported.NO
        # otherwise its UNKNOWN
        return HardwareSupported.UNKNOWN

    def get_supported_tags(self):
        return self.SUPPORTED_TAGS


class DetectorCmdline(Detector):
    """ detect hardware using cmdline helpers """

    LAPTOP_DETECT = "/usr/sbin/laptop-detect"
    SCANIMAGE = ["scanimage", "-L"]

    # hardware::laptop
    def _run_check_hardware__laptop(self):
        if os.path.exists(self.LAPTOP_DETECT):
            if subprocess.call([self.LAPTOP_DETECT]) == 0:
                return HardwareSupported.YES
            else:
                return HardwareSupported.NO
        else:
            LOG.warn(
                "No laptop-detect '%s' helper found" % self.LAPTOP_DETECT)
        return HardwareSupported.UNKOWN

    # hardware::scanner
    def _run_check_hardware__scanner(self):
        # note that this is slow to run (1-2s)
        #ver = c_int()
        #devices = c_long()
        #sane = cdll.LoadLibrary("libsane.so.1")
        #res = sane.sane_init(byref(ver), None)
        #print res, ver
        #if not res == SANE_STATUS_GOOD:
        #    return False
        #print res
        #sane.sane_get_devices(byref(devices), False)
        # device is SANE_device** device_list how to get data?
        #
        # Note: you can use multiprocessing.Pool.map to run all checks in
        # parallel
        try:
            output = subprocess.check_output(self.SCANIMAGE,
                                             universal_newlines=True)
            if output.startswith("device"):
                return HardwareSupported.YES
            else:
                return HardwareSupported.NO
        except Exception:
            LOG.warn("error running '%s'" % self.SCANIMAGE)
        return HardwareSupported.UNKNOWN

class DetectorCtypes(Detector):
    """ detect hardware using ctypes c calls """

    def __init__(self):
        self.TAG_TO_FUNC = {
            'hardware::video:opengl' : self._is_supported,
            }

    def _is_supported(self):
        return opengl.run_check()

    def is_supported(self, tag):
        if tag in self.TAG_TO_FUNC:
            func = self.TAG_TO_FUNC[tag]
            res = func()
            if res is True:
                return HardwareSupported.YES
            elif res is False:
                return HardwareSupported.NO
        return HardwareSupported.UNKNOWN

    def get_supported_tags(self):
        return list(self.TAG_TO_FUNC.keys())


class DetectorPython(Detector):
    """ detect hadware using python imports """

    # hardware::printer
    def _run_check_hardware__printer(self):
        try:
            # alternative use lpstat -p
            import cups
            c = cups.Connection()
            if len(c.getPrinters()) > 0:
                return HardwareSupported.YES
            else:
                return HardwareSupported.NO
        except ImportError:
            LOG.warn("No python-cups installed")
        except:
            LOG.exception("_run_cups_check")
        return HardwareSupported.UNKNOWN


def get_detectors():
    """ hepler that returns a list of all lowlevel detector classes """
    # introspect the detectors modules to load all availalbe detectors
    detectors = []
    for name, klass in globals().items():
        if name.startswith("Detector"):
            detectors.append(klass())
    return detectors
