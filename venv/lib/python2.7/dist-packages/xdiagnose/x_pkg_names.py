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

# Required dependency for:
#  + xorg-pkg-tools
#  + upstreamer
#  + upstream-versions
#  + xgit-checkout

import re

def compile_table(table):
    for regex in table:
        regex['rc'] = re.compile(regex['re'], re.IGNORECASE)

def invert_dict(d):
    return dict([[v,k] for k,v in d.items()])

def group_match_capitalize(match):
    return match.group(1).capitalize()

def group_match_lower(match):
    return match.group(1).lower()

deb_to_fdo_mapping = {
    # Identically named
    'libdmx':            'libdmx',
    'libfontenc':        'libfontenc',
    'liblbxutil':        'liblbxutil',
    'libpciaccess':      'libpciaccess',
    'libxkbcommon':      'libxkbcommon',
    'libxkbui':          'libxkbui',
    'libxkbfile':        'libxkbfile',
    'libxtrans':         'libxtrans',
    'wayland':           'wayland',

    # Changed names that don't follow the standard rules
    'wayland-demos':     'wayland',
    'libdrm':            'drm',
    'drm-snapshot':      'drm',
    'xorg-server':       'xserver',
    'x11proto-core':     'x11proto',
    'xfonts-encodings':  'encodings',
    'libfs':             'libFS',
    'libice':            'libICE',
    'libsm':             'libSM',
    'libxcalibrate':     'libXCalibrate',
    'libxres':           'libXRes',
    'libxscrnsaver':     'libXScrnSaver',
    'libxtrap':          'libXTrap',
    'libxprintapputil':  'libXprintAppUtil',
    'libxvmc':           'libXvMC',
    'libxprintutil':     'libXprintUtil',
}
# Note: Duplicate values will get mapped to just one key
fdo_to_deb_mapping = invert_dict(deb_to_fdo_mapping)


# "Standard" Debian-X renaming rules
fdo_to_deb_rename_rules = [
    { 're': r'^xf86-(.*)$', 'sub': r'xserver-xorg-\1', },
    { 're': r'^(.*)proto$', 'sub': r'x11proto-\1', },
]
compile_table(fdo_to_deb_rename_rules)

# Inverse of Debian-X renaming rules
deb_to_fdo_rename_rules = [
    { 're': r'^lib([a-z])',         'sub': r'lib\1',       'func': group_match_capitalize},
    { 're': r'^lib(.*)wm$',         'sub': r'lib\1WM',     },
    { 're': r'^xtrans(.*)',         'sub': r'libxtrans\1', },
    { 're': r'^x11proto-(.*)$',     'sub': r'\1proto',     },
    { 're': r'^xserver-xorg-(.*)$', 'sub': r'xf86-\1',     },
]
compile_table(deb_to_fdo_rename_rules)

def lookup(name, mapping, rules):
    if name is None:
        return None

    # Lookup the package name
    pkg = mapping.get(name, None)
    if pkg is not None:
        return pkg

    # Use standard rename rules
    for rule in rules:
        m = rule['rc'].search(name)
        if not m:
            continue
        if 'func' in rule:
            text = re.sub(rule['re'], rule['func'], name)
            pat = str(rule.get('sub',None))
            return str.replace(pat, '\\1', text)
        else:
            return rule['rc'].sub(rule['sub'], name)

    # Not found; assume the same package name applies
    return name

def debpkg_to_fdopkg(name):
    return lookup(name, deb_to_fdo_mapping, deb_to_fdo_rename_rules)

def fdopkg_to_debpkg(name):
    return lookup(name, fdo_to_deb_mapping, fdo_to_deb_rename_rules)

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: %prog <package-name>")
        sys.exit(1)

    package = sys.argv[1]

    print(lookup(package,
                 deb_to_fdo_mapping,
                 deb_to_fdo_rename_rules))
