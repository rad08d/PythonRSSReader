#!/usr/bin/python3
# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Copyright (C) 2010-2012 Bryce Harrington <bryce@canonical.com>
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import absolute_import, print_function, unicode_literals

import sys
import os
import re
import binascii

from .utils.debug import (ERR, warn, dbg)
from .utils.file_io import (load_binary, load_file)


def _bytes(edid, byte1, byte2=None):
    if byte2:
        return edid[byte1*2:(byte2+1)*2]
    else:
        return edid[byte1*2:(byte1+1)*2]

def binary_to_bytecode(filename):
    data = load_binary(filename)
    return [ binascii.b2a_hex(data).decode("utf-8") ]

def load_edid_bytecodes(filename):
    """Loads a list of unique EDIDs from a given file.

    The file could be an Xorg.0.log with multiple bytecodes, or a binary
    edid retrieved from the monitor itself, or previously saved Edid data.
    Returns a list of bytecode strings, suitable for use with the Edid
    object constructor.
    """
    if (filename is None or filename == '' or not os.path.exists(filename)):
        raise Exception("Invalid filename %s" %(filename))

    try:
        # Try loading as a plain text file first (ala Xorg.0.log)
        lines = load_file(filename)
        if len(lines) < 1:
            raise Exception("Invalid file %s" %(filename))

        if lines[0].startswith('00ffffffffffff00'):
            # Looks like a regular edid file
            return [ lines.join("\n") ]

        # Next, assume it's an Xorg.0.log
        raw_edid = ""
        re_head = re.compile("\(II\) .*\(\d+\): EDID \(in hex\):$")
        re_edid = re.compile("\(II\) .*\(\d+\):\s\t([0-9a-f]{32})$")

        seen_edid_header = False
        edid_raw = ""
        edids = []
        # TODO: Make sure only unique edids are returned
        for line in lines:
            if re_head.search(line):
                seen_edid_header = True
            elif seen_edid_header:
                m = re_edid.search(line)
                if not m:
                    edids.append(edid_raw)
                    edid_raw = ""
                    seen_edid_header = False
                    continue
                edid_raw += m.group(1)
        return edids

    except UnicodeDecodeError:
        return binary_to_bytecode(filename)

    return None


class EdidFirmware(object):
    EDID_FIRMWARE_PATH = '/lib/firmware/edid'
    EDID_DRM_CONF_PATH = '/etc/modprobe.d/drm-kms-helper.conf'

    def __init__(self):
        pass

    def list(self):
        for filename in os.listdir(self.EDID_FIRMWARE_PATH):
            edid_path = os.path.join(self.EDID_FIRMWARE_PATH, filename)
            lines = binary_to_bytecode(edid_path)
            edid = Edid("\n".join(lines))
            edid._origin = "firmware"
            yield edid

    def install(self, edid_filename):
        '''Installs the named edid file into the firmware directory'''
        import errno
        import shutil
        try:
            os.makedirs(self.EDID_FIRMWARE_PATH)
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                warn("Could not mkdir %s" %(self.EDID_FIRMWARE_PATH))
                return False

        # Install the EDID
        edid_firmware = os.path.basename(edid_filename)
        try:
            target = os.path.join(self.EDID_FIRMWARE_PATH, edid_firmware)
            shutil.copyfile(edid_filename, target)
            print("Installed %s" %(target))
            return True
        except:
            warn("Could not install firmware")
            raise
            return False

    def uninstall(self, edid_filename):
        '''Uninstalls the named edid file from the firmware directory'''
        edid_firmware = os.path.basename(edid_filename)
        try:
            target = os.path.join(self.EDID_FIRMWARE_PATH, edid_firmware)
            os.remove(target)
            print("Uninstalled %s" %(target))
            return True
        except:
            warn("Could not uninstall %s" %(target))
            raise
            return False

    def activate(self, edid_name):
        '''Activates given edid by passing it as a kernel command line parameter'''

        # TODO: Install it automatically?
        #self._install(edid_name)
        f = open(self.EDID_DRM_CONF_PATH, 'w')
        f.write("options drm_kms_helper edid_firmware=edid/%s\n" %(edid_name))
        f.close()
        print("Activated %s via %s" %(edid_name, self.EDID_DRM_CONF_PATH))
        return True

    def deactivate(self, edid_name):
        line_to_remove = "options drm_kms_helper edid_firmware=edid/%s" %(edid_name)
        f = open(self.EDID_DRM_CONF_PATH, 'w')
        lines = f.readlines()
        f.close()
        f = open(self.EDID_DRM_CONF_PATH, 'w')
        for line in lines:
            if line != line_to_remove:
                f.write(line)
        f.close()

class Edid(object):
    def __init__(self, bytecode=None):
        '''bytecode: multiline hexadecimal text such as from an Xorg.0.log'''
        self._items = None
        self._origin = None
        self.edid_raw = bytecode
        if self.edid_raw is not None:
            # TODO: Move this to top
            assert bytecode.startswith('00ffffffffffff00'), "bytecode is not valid EDID data"
            self._origin = "custom"

    def save(self, filename):
        file = open(filename, 'wb')
        file.write(self.to_binary())
        file.close()
        return True

    def _parse(self, edid):
        if edid is None:
            return None
        return [
            ("Header", _bytes(edid,0,7)),
            ("Manufacturer", _bytes(edid,8,9)),
            ("Product ID code", _bytes(edid,10,11)),
            ("Serial Number", _bytes(edid,12,15)),
            ("Week of Manufacture", _bytes(edid,16)),
            ("Year of Manufacture", _bytes(edid,17)),
            ("EDID Version", _bytes(edid,18)),
            ("EDID Revision", _bytes(edid,19)),

            ("Video input def", _bytes(edid,20)),
            ("Max Horiz Image(cm)", _bytes(edid,21)),
            ("Max Vert Image(cm)", _bytes(edid,22)),
            ("Gamma", _bytes(edid,23)),
            ("Power management", _bytes(edid,24)),

            ("Chromaticity", _bytes(edid,25,34)),
            ("Timing I", _bytes(edid,35)),
            ("Timing II", _bytes(edid,36)),
            ("Reserved Timing", _bytes(edid,37)),
            ("Standard Timing", _bytes(edid,38,53)),
            ("Horiz Active (px)", _bytes(edid,56)),
            ("Horiz Blanking", _bytes(edid,57)),
            ("Horiz high", _bytes(edid,58)),
            ("Vert Active", _bytes(edid,59)),
            ("Vert Blank", _bytes(edid,60)),
            ("Vert high", _bytes(edid,61)),
            ("Horz Sync Offset (px)", _bytes(edid,62)),
            ("Horiz Sync Pulse Width (px)", _bytes(edid,63)),
            ("Vert Sync (lines)", _bytes(edid,64)),
            ("high", _bytes(edid,65)),
            ("Horiz Image Size (mm)", _bytes(edid,66)),
            ("Vert Image Size (mm)", _bytes(edid,67)),
            ("Image Size high", _bytes(edid,68)),
            ("Horiz Border", _bytes(edid,69)),
            ("Vert Border", _bytes(edid,70)),
            ("Interlacing", _bytes(edid,71)),
            ("Descriptor Block 2", _bytes(edid,72,89)),
            ("Descriptor Block 3", _bytes(edid,90,107)),
            ("Descriptor Block 4", _bytes(edid,108,125)),
            ("Extension Flag", _bytes(edid,126)),
            ("Checksum", _bytes(edid,127)),
            ]

    def to_hex(self):
        return self.edid_raw

    def to_binary(self):
        return bytes.fromhex(self.edid_raw)

    @property
    def items(self):
        if self._items is None:
            self._items = self._parse(self.to_hex())
        return self._items

    @property
    def manufacturer(self):
        code = self.items[1][1]              # The ascii code
        bstr = str(bin(int(code, 16)))[2:]   # Converted to binary
        bstr = bstr.zfill(15)                # Fill left side with 0's
        s = [                                # Extract and convert letter codes to chars
            chr(int(bstr[-15:-10],2) + ord('A') - 1),
            chr(int(bstr[-10:-5],2) + ord('A') - 1),
            chr(int(bstr[-5:],2) + ord('A') - 1)
            ]
        return ''.join(s)

    @property
    def product_id(self):
        return _bytes(self.to_hex(),10,11)

    @property
    def serial_number(self):
        return _bytes(self.to_hex(),12,15)

    @property
    def name(self):
        return "%s:%s  SN#%s  %d-%d  v%s.%s  %s" %(
            self.manufacturer,
            self.items[2][1],
            self.items[3][1],
            int(self.items[4][1], 16),
            int(self.items[5][1], 16) + 1990,
            self.items[6][1],
            self.items[7][1],
            self._origin
            )

    def __str__(self):
        text = ''
        for field, value in self.items:
            text += "%-30s: %s\n" %(field, value)
        return text


if __name__ == "__main__":
    edidfile = sys.argv[1]
    regex = re.compile("\(II\) .*\(\d+\):\s+(.*)$")

    edid_text = ""
    lines = load_file(edidfile)
    for line in lines.split("\n"):
        m = regex.search(line)
        if m:
            line = m.group(1)
        edid_text += line

    edid = Edid(edid_text)
    print(edid)
