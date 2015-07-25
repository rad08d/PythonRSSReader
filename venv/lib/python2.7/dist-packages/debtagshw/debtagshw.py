# debtagshw: lib to detect what hardware tags apply to the current system
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
LOG=logging.getLogger(__name__)

# get the detectors lib
from . import detectors

from .enums import HardwareSupported

class DebtagsAvailableHW(object):
    """ Match the currents system hardware to debtags """
    
    def __init__(self):
        self._init_detectors()

    def _init_detectors(self):
        self._detectors = detectors.get_detectors()

    # public functions
    def get_hardware_support_for_tags(self, tags_list):
        """ Check list of tags against the hardware of the system.

            Check the given tag list and return a dict of:
             "tag" -> HardwareSupported.{YES,NO,UNKOWN}
        """
        result = {}
        for tag in tags_list:
            if not tag.startswith("hardware::"):
                continue
            result[tag] = self._check_hw_debtag(tag)
        return result

    def generate_tag_expressions(self):
        """
        Generate a sequence of (HardwareSupported, taglist)

        HardwareSupported is one of the constants defined in HardwareSupported

        taglist is a sequence of tags that applies or does not apply to the
        current system.

        The resulting positive or negative tag lists can be used to evaluate
        whether a package is suitable or not for the current system, or to list
        uninstalled packages that could use the hardware of the current system.
        """
        for detector in self._detectors:
            for supported, tags in detector.generate_tag_expressions():
                yield supported, tags

    def get_supported_tags(self):
        supported_tags = []
        for detector in self._detectors:
            supported_tags += detector.get_supported_tags()
        return supported_tags

    # private
    def _check_hw_debtag(self, tag):
        """ helper that checks a individual tag for support """
        # ask each detector
        res = HardwareSupported.UNKNOWN
        for detector in self._detectors:
            res = detector.is_supported(tag)
            if res != HardwareSupported.UNKNOWN:
                break
        return res


