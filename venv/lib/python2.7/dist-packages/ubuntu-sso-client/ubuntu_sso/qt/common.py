# -*- coding: utf-8 -*-
#
# Author: Diego Sarmentero <diego.sarmentero@canonical.com>
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
"""Common functionality used by the UI modules."""

from __future__ import unicode_literals

import re

from ubuntu_sso.utils import compat
from ubuntu_sso.utils.ui import (
    PASSWORD_DIGIT,
    PASSWORD_LENGTH,
    PASSWORD_MATCH,
    PASSWORD_MUST_CONTAIN,
    PASSWORD_UPPER,
)

# all the text + styles that are used in the gui
BAD = '<img src=":/password_hint_warning.png" /><small> %s </small>'
GOOD = '<img src=":/password_hint_ok.png" /><small> %s </small>'
NORMAL = '<small> %s </small>'


def password_assistance(line_edit, assistance, icon_type=BAD):
    """Show help for the password field."""
    text1 = compat.text_type(line_edit.text())
    label_text = ["<b>%s</b>" % PASSWORD_MUST_CONTAIN, ]

    if len(text1) < 8:
        sign = icon_type
    else:
        sign = GOOD
    label_text.append(sign % PASSWORD_LENGTH)

    if re.search('[A-Z]', text1) is None:
        sign = icon_type
    else:
        sign = GOOD
    label_text.append(sign % PASSWORD_UPPER)

    if re.search('[\d+]', text1) is None:
        sign = icon_type
    else:
        sign = GOOD
    label_text.append(sign % PASSWORD_DIGIT)

    assistance.setText("<br>".join(label_text))


def password_check_match(line_edit, line_edit_confirm, assistance):
    """Check if passwords match, otherwise show a message."""
    password_assistance(line_edit, assistance)
    label_text = compat.text_type(assistance.text())
    text1 = compat.text_type(line_edit.text())
    text2 = compat.text_type(line_edit_confirm.text())
    if text1 != text2:
        label_text += "<br>" + BAD % PASSWORD_MATCH
    assistance.setText(label_text)


def password_default_assistance(assistance):
    """Show default help for the password field."""
    label_text = ["<b>%s</b>" % PASSWORD_MUST_CONTAIN, ]
    label_text.append(NORMAL % PASSWORD_LENGTH)
    label_text.append(NORMAL % PASSWORD_UPPER)
    label_text.append(NORMAL % PASSWORD_DIGIT)
    assistance.setText("<br>".join(label_text))


def check_as_invalid(line_edit):
    """Set QLineEdit's formError property as True, refresh the style."""
    line_edit.setProperty("formError", True)
    line_edit.style().unpolish(line_edit)
    line_edit.style().polish(line_edit)


def check_as_valid(line_edit):
    """Set QLineEdit's formError property as False, refresh the style."""
    line_edit.setProperty("formError", False)
    line_edit.style().unpolish(line_edit)
    line_edit.style().polish(line_edit)
