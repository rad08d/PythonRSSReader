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


'''
This updates lines in config files matching the following syntax.  It
preserves the rest of the file contents unchanged.

PARAMETER_FIRST="some string values"
PARAMETER_SECOND=""

# This is a comment
PARAMETER_THIRD="0x01234567,0xfefefefe,0x89abcdef,0xefefefef"
PARAMETER_FOURTH=false
PARAMETER_FIFTH=42
'''

from __future__ import absolute_import, print_function, unicode_literals

import re
import os
import sys
import shutil
import fileinput

from .utils.debug import dbg

def rotated_backup(path, count=4):
    """
    Rename a file keeping up to <count> prior versions
    """
    # Rotate the old backups
    for i in range(count, 1, -1):
        old_path = "%s.bak.%d" %(path, i-1)
        new_path = "%s.bak.%d" %(path, i)
        if os.path.exists(old_path):
            shutil.move(old_path, new_path)

    new_path = old_path
    old_path = "%s.bak" %(path)
    if os.path.exists(old_path):
        shutil.move(old_path, new_path)

    new_path = old_path
    if os.path.isfile(path):
        shutil.copy(path, new_path)
    elif os.path.isdir(path):
        shutil.copytree(path, new_path)
    else:
        shutil.move(path, new_path)


def safe_backup(path, keep_original=True):
    """
    Rename a file or directory safely without overwriting an existing
    backup of the same name.
    """
    count = -1
    new_path = None
    while True:
        if os.path.exists(path):
            if count == -1:
                new_path = "%s.bak" % (path)
            else:
                new_path = "%s.bak.%s" % (path, count)
            if os.path.exists(new_path):
                count += 1
                continue
            else:
                if keep_original:
                    if os.path.islink(path):
                        linkto = os.readlink(path)
                        shutil.copy(linkto, new_path)
                    elif os.path.isfile(path):
                        shutil.copy(path, new_path)
                    elif os.path.isdir(path):
                        shutil.copytree(path, new_path)
                    else:
                        shutil.move(path, new_path)
                    break
        else:
            break
    return new_path

def config_dict(filename, delim='='):
    re_param = re.compile("^\s*(\w+)\s*"+delim+"\s*(.*)")
    data = {}
    for line in fileinput.input(filename):
        m = re_param.match(line)
        if m:
            data[m.group(1)] = m.group(2)
    return data

# TODO: Perhaps the filename should be a fileio too?
def config_update(filename, override_params=None, merge_params=None, delim='=', fileio=sys.stdout):
    '''filename is the input file.  fileio is the output stream'''
    keys = []
    if override_params:
        keys = list(override_params.keys())
    if merge_params:
        keys.extend(list(merge_params.keys()))
    keys = list(set(keys))
    keys.sort()

    dbg(filename)
    for line in fileinput.input(filename):
        dbg(line)
        new_line = line

        if merge_params is not None:
            dbg("Merging parameters")
            for key in merge_params:
                dbg(" - %s" %(key))
                p = re.compile("^\s*"+key+"\s*"+delim+"\s*(\"?)(.*)(\"?)")
                m = p.match(line)
                if m:
                    value = merge_params[key].replace('"', '')
                    if len(value)>0:
                        new_line = "%s%s%s%s %s%s\n" %(key, delim, m.group(1), m.group(2), value, m.group(3))
                    keys.remove(key)

        if override_params is not None:
            dbg("Overriding parameters")
            for key in list(override_params.keys()):
                dbg(" - %s" %(key))
                p = re.compile("^\s*"+key+"\s*"+delim)
                if p.match(line):
                    new_line = "%s%s%s\n" %(key, delim, override_params[key])
                    dbg("   delim: %s" %(delim))
                    dbg("   param: %s" %(override_params[key]))
                    if key in keys:
                        keys.remove(key)

        fileio.write(new_line)
        dbg("Wrote: %s" %(new_line))

    # Handle case of parameters that weren't already present in the file
    for key in keys:
        dbg("Adding key %s" %(key))
        if override_params and key in override_params:
            fileio.write("%s%s%s\n" %(key, delim, override_params[key]))
        elif merge_params and key in merge_params:
            fileio.write("%s%s%s\n" %(key, delim, merge_params[key]))

if __name__ == '__main__':
    filename = '/etc/default/grub'
    override_params = {
        'FOO':                        '"xyz"',
        'BOTH':                       '"correct"',
        'GRUB_DEFAULT':               2,
        'GRUB_CMDLINE_LINUX':         '"foo=bar"',
        'GRUB_HIDDEN_TIMEOUT_QUIET':  False,
        }
    merge_params = {
        'GRUB_CMDLINE_LINUX_DEFAULT': '"vesafb.invalid=1"',
        'BAR':                        'f(1&&2*$i^2) # \o/',
        'BOTH':                        '"incorrect"',
        }

    config_update(filename, override_params, None)
    config_update(filename, None,            merge_params)
    config_update(filename, override_params, merge_params)

    # TODO: Test for if drm.debug=0x4 and we want to set it to 0xe
