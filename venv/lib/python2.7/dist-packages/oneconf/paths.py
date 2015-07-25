# -*- coding: utf-8 -*-
# Copyright (C) 2011 Canonical
#
# Authors:
#  Didier Roche <didrocks@ubuntu.com>
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; version 3.
#
# This program is distributed in the hope that it will be useful, but WITHOUTa
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

import os

try:
    from configparser import NoSectionError, NoOptionError, RawConfigParser
except ImportError:
    # Python 2
    from ConfigParser import NoSectionError, NoOptionError, RawConfigParser

from xdg import BaseDirectory as xdg

ONECONF_OVERRIDE_FILE = "/tmp/oneconf.override"

ONECONF_DATADIR = '/usr/share/oneconf/data'
ONECONF_CACHE_DIR = os.path.join(xdg.xdg_cache_home, "oneconf")
PACKAGE_LIST_PREFIX = "package_list"
OTHER_HOST_FILENAME = "other_hosts"
PENDING_UPLOAD_FILENAME = "pending_upload"
HOST_DATA_FILENAME = "host"
LOGO_PREFIX = "logo"
LAST_SYNC_DATE_FILENAME = "last_sync"

_datadir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
# In both Python 2 and 3, _datadir will be a relative path, however, in Python
# 3 it will start with "./" while in Python 2 it will start with just the file
# name.  Normalize this, since the path string is used in the logo_checksum
# calculation.
if not os.path.isabs(_datadir) and not _datadir.startswith('./'):
    _datadir = os.path.join(os.curdir, _datadir)

if not os.path.exists(_datadir):
    # take the paths file if loaded from networksync module
    #
    # 2014-03-17 barry: It's probably not a good idea to use __file__, since
    # the behavior of that has changed between Python 3.3 and 3.4.  Prior to
    # 3.4, __file__ was a relative path, but in 3.4 it became absolute (which
    # it always should have been).  Because the file's *path* is the input to
    # the logo checksum (as opposed to the file's contents, because...?) this
    # value actually matters.
    #
    # However, making the FAKE_WALLPAPER path below absolute breaks the
    # package's build because inside a chroot, the absolute path of __file__
    # is unpredictable.  LP: #1269898.
    #
    # The solution then is to make the FAKE_WALLPAPER path relative to the
    # current working directory, via os.path.relpath().  So first, we ensure
    # it's absolute (for older Pythons) and then relpath it.  *That's* the
    # path that will be the input to the SHA224 checksum.
    parent = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    _datadir = os.path.join(parent, "data")
if not os.path.exists(_datadir):
    _datadir = ONECONF_DATADIR
LOGO_BASE_FILENAME = os.path.join(_datadir, 'images', 'computer.png')
WEBCATALOG_SILO_DIR = "/tmp"
FAKE_WALLPAPER = None # Fake wallpaper for tests
FAKE_WALLPAPER_MTIME = None # Fake wallpaper for tests

config = RawConfigParser()
try:
    config.read(ONECONF_OVERRIDE_FILE)
    ONECONF_CACHE_DIR = config.get('TestSuite', 'ONECONF_CACHE_DIR')
    WEBCATALOG_SILO_DIR = config.get('TestSuite', 'WEBCATALOG_SILO_DIR')
    FAKE_WALLPAPER = os.path.relpath(os.path.abspath(os.path.join(
        os.path.dirname(_datadir), config.get('TestSuite', 'FAKE_WALLPAPER'))))
    try:
        FAKE_WALLPAPER_MTIME = config.get('TestSuite', 'FAKE_WALLPAPER_MTIME')
    except NoOptionError:
        FAKE_WALLPAPER_MTIME = None
except NoSectionError:
    pass
WEBCATALOG_SILO_SOURCE = os.path.join(WEBCATALOG_SILO_DIR, "source")
WEBCATALOG_SILO_RESULT = os.path.join(WEBCATALOG_SILO_DIR, "result")
