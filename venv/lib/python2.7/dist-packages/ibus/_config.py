# vim:set et sts=4 sw=4:
#
# ibus - The Input Bus
#
# Copyright (c) 2007-2008 Peng Huang <shawn.p.huang@gmail.com>
# Copyright (c) 2007-2008 Red Hat, Inc.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301
# USA

__all__ = (
    "get_version",
    "get_copyright",
    "get_license",
    "get_ICON_KEYBOARD",
    "LIBIBUS_SONAME",
    "ISOCODES_PREFIX",
    "_"
)

import gettext

_ = lambda a: gettext.dgettext("ibus10", a)

def get_version():
	return '1.5.5'

def get_copyright():
    return _('''Copyright (c) 2007-2010 Peng Huang
Copyright (c) 2007-2010 Red Hat, Inc.''')

def get_license():
    return 'LGPL'

def get_ICON_KEYBOARD():
    import gtk
    icon = 'ibus-keyboard'
    fallback_icon = 'ibus-keyboard'
    settings = gtk.settings_get_default()
    if settings.get_property('gtk-icon-theme-name') != 'gnome':
        return fallback_icon
    theme = gtk.icon_theme_get_default()
    if not theme.lookup_icon(icon, 18, 0):
        return fallback_icon
    return icon

LIBIBUS_SONAME='libibus-1.0.so.5'
ISOCODES_PREFIX='/usr'
