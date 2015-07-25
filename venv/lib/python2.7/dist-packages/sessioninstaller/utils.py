#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""util -- Apt-Xapian-Index integration"""
# Copyright (c) 2010 Sebastian Heinlein <devel@glatzor.de>
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
__state__   = "experimental"

import logging
import os

from xdg.DesktopEntry import DesktopEntry

__ALL__ = ("get_package_desc", "APP_INSTALL_DATA", "AXI_DATABASE")

APP_INSTALL_DATA = "/usr/share/app-install/desktop"
AXI_DATABASE = "/var/lib/apt-xapian-index/index"

log = logging.getLogger("sessioninstaller")

try:
    import xapian
    os.stat(APP_INSTALL_DATA)
    axi = xapian.Database("/var/lib/apt-xapian-index/index")
except (ImportError, OSError, xapian.DatabaseOpeningError):
    log.warning("Falling back to package information")
    axi = None

_desktop_cache = {}

def _load(file_name):
    path = os.path.join(APP_INSTALL_DATA, file_name)
    return DesktopEntry(path)

def get_package_desc(pkg, summary):
    """Return a pango markup description of the package.
    If the package provides one or more applications
    use the name and comment of the applications.
    """
    markup = ""
    try:
        pkg, arch = pkg.split(":")
    except ValueError:
        arch = None
    if axi:
        for m in axi.postlist("XP" + pkg):
            doc = axi.get_document(m.docid)
            for term_iter in doc.termlist():
                app = False
                if term_iter.term.startswith("XDF"):
                    if markup:
                        markup += "\n\n"
                    file_name = term_iter.term[3:]
                    de = _desktop_cache.setdefault(file_name, _load(file_name))
                    app_name = de.getName()
                    app_comment = de.getComment()
                    if app_name:
                        markup += "<b>%s" % app_name
                        if arch:
                            markup += " (%s)" % arch
                        markup += "</b>"
                        if app_comment:
                            markup += "\n%s" % app_comment
    if not markup:
        if arch:
            markup = "<b>%s (%s)</b>" % (pkg, arch)
        else:
            markup = "<b>%s</b>" % pkg
        if summary:
            markup += "\n%s" % summary
    return markup

def get_process_cmdline(pid):
    """Return the command line arguments of the given process as a list.

    :param pid: a process id
    """
    with open("/proc/%s/cmdline" % pid) as fd_cmd:
         return [arg for arg in fd_cmd.read().split("\x00") if arg]

def get_process_ppid(pid):
    """Return the process id of the parent process.

    :param pid: a process id
    """
    with open("/proc/%s/status" % pid) as fd_status:
        for line in fd_status:
            if line.startswith("PPid:"):
                return int(line.split()[1])
        return None

def get_process_exe(pid):
    """Return the path to the executable of the given process or
    None if if cannot be found.

    :param pid: a process id
    """
    # Taken from python-psutil
    link_exe = "/proc/%s/exe" % pid
    try:
        exe = os.readlink(link_exe)
    except (OSError, IOError):
        return None
    # Remove null bytes
    exe = exe.replace("\x00", "")
    # Handle deleted files
    if exe.endswith(" (deleted)") and not os.path.exists(exe):
        exe = exe[:-10]
    return exe

# vim:ts=4:sw=4:et
