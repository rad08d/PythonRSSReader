#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Provides a dummy backend."""
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

from gettext import gettext as _

from gi.repository import Gtk

class DummyBackend(object):

    """Provide some dummy dialogs which simulate package operations."""

    def _show_message(self, title, text):
        dia = Gtk.MessageDialog(buttons=Gtk.ButtonsType.CLOSE, message_format=title)
        dia.format_secondary_text(text)
        dia.run()
        dia.hide()

    def remove_packages(self, xid, package_names, interaction):
        title = _("Removing packages")
        text = _("The following packages will be removed with interaction "
                 "mode %s: %s") % ( interaction, " ".join(package_names))
        self._show_message(title, text)

    def install_packages(self, xid, package_names, interaction):
        title = _("Installing packages")
        text = _("The following packages will be installed with interaction "
                 "mode %s: %s") % (interaction, " ".join(package_names))
        self._show_message(title, text)

    def install_package_files(self, xid, package_names, interaction):
        title = _("Installing package files")
        text = _("The following package files will be installed with "
                 "interaction mode %s: %s") % (interaction,
                                               " ".join(package_names))
        self._show_message(title, text)

# vim:ts=4:sw=4:et
