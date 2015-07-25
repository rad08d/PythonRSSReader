# -*- coding: utf-8 -*-

# Authors: Diego Sarmentero <diego.sarmentero@canonical.com>
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
"""Customized Check Box to support links."""

from PyQt4 import QtGui, QtCore


class EnhancedCheckBox(QtGui.QCheckBox):
    """Enhanced QCheckBox to support links in the message displayed."""

    def __init__(self, text="", parent=None):
        QtGui.QCheckBox.__init__(self, parent)
        hbox = QtGui.QHBoxLayout()
        hbox.setAlignment(QtCore.Qt.AlignLeft)
        self.text_label = QtGui.QLabel(text)
        self.text_label.setWordWrap(True)
        self.text_label.setOpenExternalLinks(True)
        padding = self.iconSize().width()
        self.text_label.setStyleSheet("margin-top: -3px;"
                                      "padding-left: 2px;")
        hbox.setContentsMargins(padding, 0, 0, 0)
        hbox.addWidget(self.text_label)
        self.setLayout(hbox)

        if parent is not None:
            lines = self.text_label.width() / float(parent.width())
            self.text_label.setMinimumWidth(parent.width())
            self.setMinimumHeight(self.height() * lines)

        self.stateChanged.connect(self.text_label.setFocus)

    def text(self):
        """Return the text of this widget."""
        return self.text_label.text()

    # Invalid name "setText"
    # pylint: disable=C0103

    def setText(self, text):
        """Set a new text to this widget."""
        self.text_label.setText(text)

    # pylint: enable=C0103
