#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Make use of synaptic as backend."""
# Copyright (C) 2008-2010 Sebastian Heinlein <devel@glatzor.de>
# Copyright (C) 2005-2007 Canonical
#
# Licensed under the GNU General Public License Version 2
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
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

__author__ = "Sebastian Heinlein <devel@glatzor.de>, " \
             "Michael Vogt <mvo@canonical.com"

import tempfile
from gettext import gettext as _

from gi.repository import GObject

from defer import Deferred

import sessioninstaller.errors


class SynapticBackend(object):

    """Make use of Synaptic to install and remove packages."""

    def _run_synaptic(self, xid, opt, tempf, interaction):
        deferred = Deferred()
        if tempf:
            opt.extend(["--set-selections-file", "%s" % tempf.name])
        #FIXME: Take interaction into account
        opt.extend(["-o", "Synaptic::closeZvt=true"])
        if xid:
            opt.extend(["--parent-window-id", "%s" % (xid)])
        cmd = ["/usr/bin/gksu", 
               "--desktop", "/usr/share/applications/update-manager.desktop",
               "--", "/usr/sbin/synaptic", "--hide-main-window",
               "--non-interactive"]
        cmd.extend(opt)
        flags = GObject.SPAWN_DO_NOT_REAP_CHILD
        (pid, stdin, stdout, stderr) = GObject.spawn_async(cmd, flags=flags)
        GObject.child_watch_add(pid, self._on_synaptic_exit, (tempf, deferred))
        return deferred

    def _on_synaptic_exit(self, pid, condition, (tempf, deferred)):
        if tempf:
            tempf.close()
        if condition == 0:
            deferred.callback()
        else:
            deferred.errback(sessioninstaller.errors.ModifyFailed())

    def remove_packages(self, xid, package_names, interaction):
        opt = []
        # custom progress strings
        #opt.append("--progress-str")
        #opt.append("%s" % _("Please wait, this can take some time."))
        #opt.append("--finish-str")
        #opt.append("%s" %  _("Update is complete"))
        tempf = tempfile.NamedTemporaryFile()
        for pkg_name in package_names:
            tempf.write("%s\tuninstall\n" % pkg_name)
        tempf.flush()
        return self._run_synaptic(xid, opt, tempf, interaction)

    def install_packages(self, xid, package_names, interaction):
        opt = []
        # custom progress strings
        #opt.append("--progress-str")
        #opt.append("%s" % _("Please wait, this can take some time."))
        #opt.append("--finish-str")
        #opt.append("%s" %  _("Update is complete"))
        tempf = tempfile.NamedTemporaryFile()
        for pkg_name in package_names:
            tempf.write("%s\tinstall\n" % pkg_name)
        tempf.flush()
        return self._run_synaptic(xid, opt, tempf, interaction)

    def install_package_files(self, xid, package_names, interaction):
        raise NotImplemented


# vim:ts=4:sw=4:et
