# -*- coding: utf-8 -*-
#
# Copyright 2011-2012 Canonical Ltd.
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
"""The Qt graphical interface for the Ubuntu Single Sign On Client."""

from __future__ import unicode_literals

import sys
import collections

from PyQt4 import QtGui, QtCore

from ubuntu_sso.logger import setup_gui_logging
from ubuntu_sso.utils.ui import GENERIC_BACKEND_ERROR

logger = setup_gui_logging('ubuntu_sso.qt')

LINK_STYLE = ('<a href="{link_url}">'
              '<span style="color:#df2d1f;">{link_text}</span></a>')
ERROR_ALL = '__all__'
ERROR_STYLE = '<font color="#df2d1f" style="font-size:small"><b>%s</b></font>'
ERROR_MESSAGE = 'message'
PREFERED_UI_SIZE = {'width': 550, 'height': 525}
TITLE_STYLE = '<span style="font-size:xx-large;font-weight:bold;">%s</span>'
WINDOW_TITLE = 'Ubuntu Single Sign On'

# TODO: There is a pixel discrepancy between Qt on Linux and Windows
# and Mac OS X. On Mac OS X, one test fails with the height being
# off. For now, we're forcing a different UI height on darwin.
if sys.platform == 'darwin':
    PREFERED_UI_SIZE['height'] = 533


def build_general_error_message(errordict):
    """Build a user-friendly error message from the errordict."""
    logger.debug('build_general_error_message: errordict is: %r.', errordict)
    result = ''
    if isinstance(errordict, collections.Mapping):
        msg1 = errordict.get(ERROR_ALL)
        msg2 = errordict.get(ERROR_MESSAGE)
        if msg2 is None:
            # See the errordict in LP: 828417
            msg2 = errordict.get('error_message')
        if msg1 is not None and msg2 is not None:
            result = '\n'.join((msg1, msg2))
        elif msg1 is not None:
            result = msg1
        elif msg2 is not None:
            result = msg2
        else:
            if 'errtype' in errordict:
                del errordict['errtype']
            result = '\n'.join(
                [('%s: %s' % (k, v)) for k, v in errordict.items()])
    else:
        result = GENERIC_BACKEND_ERROR
        logger.error('build_general_error_message with unknown error: %r',
            errordict)

    logger.info('build_general_error_message: returning %r.', result)
    return result


def maybe_elide_text(label, text, width, markup=None):
    """Set 'text' to be the 'label's text.

    If 'text' is longer than 'width', set the label's tooltip to be the full
    text, and the text itself to be the elided version of 'text'.

    """
    fm = QtGui.QFontMetrics(label.font())
    elided_text = fm.elidedText(text, QtCore.Qt.ElideRight, width)
    if elided_text != text:
        label.setToolTip(text)
    if markup is not None:
        elided_text = markup % elided_text
    label.setText(elided_text)
