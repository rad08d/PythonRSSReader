#!/usr/bin/python3
# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-

#========================================================================
#
# xlogparse
#
# DESCRIPTION
#
# Parses Xlog.*.log format files and allows looking up data from it
#
# AUTHOR
#   Bryce W. Harrington <bryce@canonical.com>
#
# COPYRIGHT
#   Copyright (C) 2010-2012 Bryce W. Harrington
#   All Rights Reserved.
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
#
#========================================================================

from __future__ import absolute_import, print_function, unicode_literals

import re

class XorgLog(object):

    def __init__(self, logfile=None):
        self.devices  = [ ]
        self.modules  = [ ]
        self.errors   = [ ]
        self.warnings = [ ]
        self.info     = [ ]
        self.notimpl  = [ ]
        self.notices  = [ ]
        self.displays = { }
        self.xserver_version = None
        self.boot_time = None
        self.boot_logfile = None
        self.kernel_version = None
        self.video_driver = None
        self.xorg_conf_path = None
        self.logfile = logfile

        if logfile:
            self.parse(logfile)

    def add_device(self, device, devclass, devtype):
        device = {
            'name':         device,
            'class':        devclass,
            'type':         devtype
            }
        self.devices.append(device)

    def parse(self, filename):
        self.displays = {}
        display = {}
        display_name = "Unknown"
        in_file = open(filename, "r")
        gathering_module = False
        found_ddx = False
        module = None
        for line in in_file.readlines():
            #print("Line: %s" % (line))

            # TODO: PCI
            # TODO: extensions

            # Modules and Devices
            m = re.search(r'\(..\)', line)
            if m:
                if gathering_module and module is not None:
                    self.modules.append(module)
                gathering_module = False
                module = None

                m = re.search('\(II\) Loading.*modules\/drivers\/(.+)_drv\.so', line)
                if m:
                    found_ddx = True

                m = re.search(r'\(II\) Module (\w+):', line)
                if m:
                    module = {
                        'name':         m.group(1),
                        'vendor':       None,
                        'version':      None,
                        'class':        None,
                        'abi_name':     None,
                        'abi_version':  None,
                        'ddx':          found_ddx,
                        }
                    found_ddx = False
                    gathering_module = True

            if gathering_module:
                   m = re.search(r'vendor="(.*:?)"', line)
                   if m:
                       module['vendor'] = m.group(1)

                   m = re.search(r'module version = (.*)', line)
                   if m:
                       module['version'] = m.group(1)

                   m = re.search(r'class: (.*)', line)
                   if m:
                       module['class'] = m.group(1)

                   m = re.search(r'ABI class:\s+(.*:?), version\s+(.*:?)', line)
                   if m:
                       if m.group(1)[:5] == "X.Org":
                           module['abi_name'] = m.group(1)[6:]
                       else:
                           module['abi_name'] = m.group(1)
                       module['abi_version'] = m.group(2)
                   continue

            # General details
            m = re.search(r'Current Operating System: (.*)$', line)
            if m:
                uname = m.group(1)
                self.kernel_version = uname.split()[2]
                continue

            m = re.search(r'Kernel command line: (.*)$', line)
            if m:
                self.kernel_command_line = m.group(1)
                continue

            m = re.search(r'Build Date: (.*)$', line)
            if m:
                self.kernel_command_line = m.group(1)
                continue

            m = re.search(r'Log file: "(.*)", Time: (.*)$', line)
            if m:
                self.boot_logfile = m.group(1)
                self.boot_time = m.group(2)

            m = re.search(r'xorg-server ([^ ]+) .*$', line)
            if m:
                self.xserver_version = m.group(1)
                continue

            m = re.search(r'Using a default monitor configuration.', line)
            if m and self.xorg_conf_path is None:
                self.xorg_conf_path = 'default'
                continue

            m = re.search(r'Using config file: "(.*)"', line)
            if m:
                self.xorg_conf_path = m.group(1)
                continue

            # EDID and Modelines
            m = re.search(r'\(II\) (.*)\(\d+\): EDID for output (.*)', line)
            if m:
                self.displays[display_name] = display
                self.video_driver = m.group(1)
                display_name = m.group(2)
                display = {'Output': display_name}
                continue

            m = re.search(r'\(II\) (.*)\(\d+\): Assigned Display Device: (.*)$', line)
            if m:
                self.displays[display_name] = display
                self.video_driver = m.group(1)
                display_name = m.group(2)
                display = {'Output': display_name}
                continue

            m = re.search(r'Manufacturer: (.*) *Model: (.*) *Serial#: (.*)', line)
            if m:
                display['display manufacturer'] = m.group(1)
                display['display model']        = m.group(2)
                display['display serial no.']   = m.group(3)

            m = re.search(r'EDID Version: (.*)', line)
            if m:
                display['display edid version'] = m.group(1)

            m = re.search(r'EDID vendor \"(.*)\", prod id (.*)', line)
            if m:
                display['vendor'] = m.group(1)
                display['product id'] = m.group(2)

            m = re.search(r'Max Image Size \[(.*)\]: *horiz.: (.*) *vert.: (.*)', line)
            if m:
                display['size max horizontal'] = "%s %s" %(m.group(2), m.group(1))
                display['size max vertical'] = "%s %s" %(m.group(3), m.group(1))

            m = re.search(r'Image Size: *(.*) x (.*) (.*)', line)
            if m:
                display['size horizontal'] = "%s %s" %(m.group(1), m.group(3))
                display['size vertical'] = "%s %s" %(m.group(2), m.group(3))

            m = re.search(r'(.*) is preferred mode', line)
            if m:
                display['mode preferred'] = m.group(1)

            m = re.search(r'Modeline \"(\d+)x(\d+)\"x([0-9\.]+) *(.*)$', line)
            if m:
                key = "mode %sx%s@%s" %(m.group(1), m.group(2), m.group(3))
                display[key] = m.group(4)
                continue

            # Errors and Warnings
            m = re.search(r'\(WW\) (.*)$', line)
            if m:
                self.warnings.append(m.group(1))
                continue

            m = re.search(r'\(EE\) (.*)$', line)
            if m:
                self.errors.append(m.group(1))
                continue

            m = re.search(r'XINPUT: Adding extended input device "(.*:?)" \(type:\s+(.*:?)\)', line)
            if m:
                self.add_device(m.group(1), 'input', m.group(2))

        if display_name not in self.displays.keys():
            self.displays[display_name] = display
        in_file.close()


    def outputs_table(self):
        s = ''
        values = {}
        n = 0
        outputs = list(self.displays.keys())
        outputs.sort()
        for output in outputs:
            display = self.displays[output]
            if display == {}:
                continue
            for key in display.keys():
                val = display.get(key, '')
                if key not in values.keys():
                    values[key] = []
                    for i in range(0,n):
                        values[key].append('')
                values[key].append(val.strip())
            n += 1

        keys = list(values.keys())
        keys.sort()
        for key in keys:
            if key[:4] == 'mode':
                continue
            s += "%-30s " %(key)
            for val in values[key]:
                s += "%15s " %(val)
            s += "\n"

        return s

    def devices_table(self):
        s = ''
        for device in self.devices:
            s += "%-12s %-20s %-s\n" %(device['class'], device['name'], device['type'])
        return s

    def modules_table(self):
        s = ''
        s += "%-10s %-10s %5s %-30s %-s\n" %("Module", "Version", "ABI", "", "Vendor")
        lines = []
        for module in self.modules:
            abi_name = module['abi_name']
            lines.append("%-10s %-10s %5s %-30s %-s" %(
                module['name'], module['version'], module['abi_version'], module['abi_name'], module['vendor']))
        lines = list(set(lines))
        lines.sort()
        s += "\n".join(lines)
        s += "\n"
        return s

    def errors_filtered(self):
        excludes = set([
            'error, (NI) not implemented, (??) unknown.',
            'Failed to load module "fglrx" (module does not exist, 0)',
            'Failed to load module "nv" (module does not exist, 0)',
            ])
        return [err for err in self.errors if err not in excludes]

    def warnings_filtered(self):
        excludes = set([
            'warning, (EE) error, (NI) not implemented, (??) unknown.',
            'The directory "/usr/share/fonts/X11/cyrillic" does not exist.',
            'The directory "/usr/share/fonts/X11/100dpi/" does not exist.',
            'The directory "/usr/share/fonts/X11/75dpi/" does not exist.',
            'The directory "/usr/share/fonts/X11/100dpi" does not exist.',
            'The directory "/usr/share/fonts/X11/75dpi" does not exist.',
            'Warning, couldn\'t open module nv',
            'Warning, couldn\'t open module fglrx',
            'Falling back to old probe method for vesa',
            'Falling back to old probe method for fbdev',
            ])
        return [err for err in self.warnings if err not in excludes]


    def __str__(self):
        s = self.logfile + ":\n"
        s += "%15s : %s\n" %("Version", self.xserver_version)
        s += "%15s : %s\n" %("Boot Time", self.boot_time)
        s += "%15s : %s\n" %("Logfile", self.boot_logfile)
        s += "%15s : %s\n" %("Config File", self.xorg_conf_path)
        if self.video_driver is None:
            s += "%15s : Unknown\n" %("Video Driver")
        else:
            s += "%15s : %s\n" %("Video Driver", self.video_driver.lower())
        s += "%15s : %s\n" %("Kernel", self.kernel_version)
        s += "\n"
        s += self.modules_table()
        s += "\n"
        s += "Outputs:\n"
        s += self.outputs_table()
        s += "\n"
        s += "Devices:\n"
        s += self.devices_table()
        s += "\n"
        s += "Errors:\n"
        s += "\n".join(self.errors_filtered())
        s += "\n"
        s += "Warnings:\n"
        s += "\n".join(self.warnings_filtered())
        return s

    def process_record(self, text):
        print("TODO")

        self.add_device(device)
        self.add_module(module)

def loadfile(filename, binary=False):
    opentype = "r"
    if binary:
        opentype += "b"
    in_file = open(filename, opentype)
    text = in_file.read()
    in_file.close()
    return text

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        xlog = XorgLog("/var/log/Xorg.0.log")
    else:
        xlog = XorgLog(sys.argv[1])
    print(xlog)

# TODO:  If size == 0x0, handle as a no-edid bug
# TODO:  If no mode preferred mentioned
# TODO:  If no modes found
# TODO:  If max size <10 or >80
# TODO:  Look up errors on http://www.x.org/wiki/FAQErrorMessages
