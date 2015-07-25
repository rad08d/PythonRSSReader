#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Provides plugins for AptDaemon"""
# Copyright (C) 2011 Canonical Ltd.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

__author__  = "Sebastian Heinlein <devel@glatzor.de>"

import apt_pkg
import os
import subprocess
import time

from gi.repository import GLib

from aptdaemon.errors import TransactionFailed
from aptdaemon.enums import ERROR_LICENSE_KEY_DOWNLOAD_FAILED


def get_license_key(uid, pkg_name, json_token, server_name):
    """Return the license key and the path for the given package."""
    rootdir = apt_pkg.config["Dir"]
    license_key_helper = os.path.join(rootdir, "usr/share/software-center/ubuntu-license-key-helper")
    cmd = [license_key_helper, "--server", server_name, "--pkgname", pkg_name]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            preexec_fn=lambda: os.setuid(uid),
                            close_fds=True,
                            # this will give us str in py3 instead of bytes
                            universal_newlines=True)
    # send json token to the process
    proc.stdin.write(json_token + "\n")
    # wait until it finishes
    while proc.poll() is None:
        while GLib.main_context_default().pending():
            GLib.main_context_default().iteration()
            time.sleep(0.05)

    if proc.returncode != 0:
        stderr = proc.stderr.read()
        raise TransactionFailed(ERROR_LICENSE_KEY_DOWNLOAD_FAILED, stderr)

    # get data from stdout
    license_key_path = proc.stdout.readline().strip()
    license_key = proc.stdout.read()

    return license_key, license_key_path
