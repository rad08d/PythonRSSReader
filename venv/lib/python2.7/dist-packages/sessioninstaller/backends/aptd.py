#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Provides an aptdaemon based backend
"""
# Copyright (C) 2008-2010 Sebastian Heinlein <devel@glatzor.de>
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

__author__ = "Sebastian Heinlein <devel@glatzor.de>"

from gi.repository import Gtk

from aptdaemon import enums
import defer
import aptdaemon.client
import aptdaemon.errors
import aptdaemon.gtk3widgets

import sessioninstaller.errors


class AptDaemonBackend(object):

    """Provides a graphical test application."""

    def __init__(self):
        self.ac = aptdaemon.client.AptClient()

    def _run_trans(self, trans, parent, interaction):
        deferred = defer.Deferred()
        dia = aptdaemon.gtk3widgets.AptProgressDialog(trans)
        if parent:
            dia.realize()
            dia.set_transient_for(parent)
        dia.run(close_on_finished=True, show_error=False,
                reply_handler=lambda: True,
                error_handler=deferred.errback)
        dia.connect("finished", self._on_finished, deferred, trans)
        return deferred

    def _on_finished(self, diag, deferred, trans):
        if deferred.called:
            return  # Already called, likely from error_handler (LP: #1056545)
        if trans.error:
            deferred.errback(trans.error)
        else:
            deferred.callback()

    def _simulate_trans(self, trans, parent, interaction):
        deferred = defer.Deferred()
        trans.simulate(reply_handler=lambda: deferred.callback(trans),
                       error_handler=deferred.errback)
        return deferred

    def _confirm_deps(self, trans, parent, interaction):
        if not [pkgs for pkgs in trans.dependencies if pkgs]:
            return trans
        dia = aptdaemon.gtk3widgets.AptConfirmDialog(trans)
        if parent:
            dia.realize()
            dia.set_transient_for(parent)
        res = dia.run()
        dia.hide()
        if res == Gtk.ResponseType.OK:
            return trans
        raise sessioninstaller.errors.ModifyCancelled

    def install_packages(self, xid, package_names, interaction):
        deferred = defer.Deferred()
        parent = None # should get from XID, but removed from Gdk 3
        self.ac.install_packages(package_names, reply_handler=deferred.callback,
                                 error_handler=deferred.errback)
        deferred.add_callback(self._simulate_trans, parent, interaction)
        deferred.add_callback(self._confirm_deps, parent, interaction)
        deferred.add_callback(self._run_trans, parent, interaction)
        deferred.add_errback(self._show_error, parent)
        return deferred

    def install_package_files(self, xid, files, interaction):
        deferred = defer.Deferred()
        parent = None # should get from XID, but removed from Gdk 3
        #FIXME: Add support for installing serveral files at the same time
        self.ac.install_file(files[0], reply_handler=deferred.callback,
                             error_handler=deferred.errback)
        deferred.add_callback(self._simulate_trans, parent, interaction)
        deferred.add_callback(self._confirm_deps, parent, interaction)
        deferred.add_callback(self._run_trans, parent, interaction)
        deferred.add_errback(self._show_error, parent)
        return deferred

    def remove_packages(self, xid, package_names, interaction):
        deferred = defer.Deferred()
        parent = None # should get from XID, but removed from Gdk 3
        self.ac.remove_packages(package_names, reply_handler=deferred.callback,
                                error_handler=deferred.errback)
        deferred.add_callback(self._simulate_trans, parent, interaction)
        deferred.add_callback(self._confirm_deps, parent, interaction)
        deferred.add_callback(self._run_trans, parent, interaction)
        deferred.add_errback(self._show_error, parent)
        return deferred

    def _show_error(self, error, parent):
        try:
            error.raise_exception()
        except aptdaemon.errors.NotAuthorizedError:
            raise sessioninstaller.errors.ModifyForbidden
        except aptdaemon.errors.TransactionCancelled:
            raise sessioninstaller.errors.ModifyCancelled
        except aptdaemon.errors.TransactionFailed, error:
            pass
        except sessioninstaller.errors.ModifyCancelled, error:
            raise error
        except Exception, error:
            error = aptdaemon.errors.TransactionFailed(enums.ERROR_UNKNOWN,
                                                       str(error))
        dia = aptdaemon.gtk3widgets.AptErrorDialog(error)
        if parent:
            dia.realize()
            dia.set_transient_for(parent)
        dia.run()
        dia.hide()
        msg = "%s - %s\n%s" % (enums.get_error_string_from_enum(error.code),
                              enums.get_error_description_from_enum(error.code),
                              error.details)
        raise sessioninstaller.errors.ModifyFailed(msg)


# vim:ts=4:sw=4:et
