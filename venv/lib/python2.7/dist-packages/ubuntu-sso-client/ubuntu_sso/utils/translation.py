# -*- coding: utf-8 -*-
#
# Copyright 2012 Canonical Ltd.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# In addition, as a special exception, the copyright holders give
# permission to link the code of portions of this program with the
# OpenSSL library under certain conditions as described in each
# individual source file, and distribute linked combinations
# including the two.
# You must obey the GNU General Public License in all respects
# for all of the code used other than OpenSSL.  If you modify
# file(s) with this exception, you may extend this exception to your
# version of the file(s), but you are not obligated to do so.  If you
# do not wish to do so, delete this exception statement from your
# version.  If you delete this exception statement from all source
# files in the program, then also delete it here.
"""Platform-specific translation functions."""

import gettext
import os
import sys

from ubuntu_sso.logger import setup_logging

logger = setup_logging('ubuntu_sso.utils.translation')


def _get_languages():
    """list of langs ordered by preference, or None for gettext defaults."""
    if sys.platform == 'darwin':
        from Cocoa import NSUserDefaults
        su = NSUserDefaults.standardUserDefaults()
        return su['AppleLanguages']
    else:
        if sys.platform == 'win32':
            return None
        return None


def _get_translations_data_path(fallback_path=None):
    """path to compiled translation files, or None for gettext defaults"""
    if getattr(sys, 'frozen', None) is not None:
        if sys.platform == 'darwin':
            main_app_dir = ''.join(__file__.partition('.app')[:-1])
            path = os.path.join(main_app_dir, 'Contents', 'Resources',
                                'translations')
            return path
        elif sys.platform == 'win32':
            return None         # TODO

    exists = (os.path.exists(fallback_path)
              if fallback_path else False)
    logger.debug("Using fallback translation path %r "
                 "which does %s exist." %
                 (fallback_path, "" if exists else "**NOT**"))

    return fallback_path


def get_gettext(translation_domain, fallback_path=None):
    """Get proper gettext translation function for platform and py version."""
    languages = _get_languages()
    translations_path = _get_translations_data_path(fallback_path)

    if languages is None or translations_path is None or languages[0] == 'en':
        logger.debug('Using default gettext translation search paths')

        translation = gettext.translation(translation_domain, fallback=True)
    else:
        translation = gettext.translation(translation_domain,
                                          translations_path,
                                          languages=languages[:1],
                                          fallback=True)
    if isinstance(translation, gettext.NullTranslations):
        logger.warn('Translations not found, using null translator.')
    if sys.version_info < (3,):
        return translation.ugettext
    else:
        return translation.gettext
