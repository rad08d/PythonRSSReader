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
"""Loading animation over a widget."""

from __future__ import unicode_literals

from PyQt4 import QtGui, QtCore

from ubuntu_sso.qt.ui import loadingoverlay_ui
from ubuntu_sso.utils.ui import LOADING_OVERLAY

LOADING_STYLE = '<span style="font-size:x-large;">{0}</span>'


class LoadingOverlay(QtGui.QFrame):
    """The widget that shows a loading animation and disable the widget below.

    In order to have this working, the Widget which is going to use this
    overlay has to reimplement the resizeEvent as follows:

    def resizeEvent(self, event):
        self.overlay.resize(event.size())
        event.accept()

    """

    def __init__(self, parent=None):
        super(LoadingOverlay, self).__init__(parent=parent)
        self.ui = loadingoverlay_ui.Ui_Form()
        self.ui.setupUi(self)

        self.timer = None
        self.counter = 0
        self.orientation = False

        self.ui.label.setText(LOADING_STYLE.format(LOADING_OVERLAY))

    # Invalid name "paintEvent", "eventFilter", "showEvent", "timerEvent"
    # pylint: disable=C0103

    def paintEvent(self, event):
        """Paint over the widget to overlay its content."""
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.TextAntialiasing, True)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        painter.fillRect(event.rect(), QtGui.QBrush(
            QtGui.QColor(255, 255, 255, 135)))
        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        painter.end()
        QtGui.QFrame.paintEvent(self, event)

    def eventFilter(self, obj, event):
        """Filter events from Frame content to draw the dot animation."""
        if getattr(self, 'ui', None) is not None and \
           obj == self.ui.frm_box and event.type() == QtCore.QEvent.Paint:
            painter = QtGui.QPainter()
            painter.begin(obj)
            painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
            pos_x = self.ui.frm_box.width() / 3
            x_padding = pos_x / 5
            for i in range(5):
                if self.counter != i:
                    linear_gradient = QtGui.QLinearGradient(
                        pos_x + (x_padding * i),
                        self.ui.frm_box.height() / 2 + 10,
                        pos_x + (x_padding * i) + 15,
                        self.ui.frm_box.height() / 2 + 25)
                    linear_gradient.setColorAt(0, QtGui.QColor(205, 200, 198))
                    linear_gradient.setColorAt(1, QtGui.QColor(237, 237, 237))
                    painter.setBrush(QtGui.QBrush(linear_gradient))
                else:
                    linear_gradient = QtGui.QLinearGradient(
                        pos_x + (x_padding * i),
                        self.ui.frm_box.height() / 2 + 10,
                        pos_x + (x_padding * i) + 15,
                        self.ui.frm_box.height() / 2 + 25)
                    linear_gradient.setColorAt(0, QtGui.QColor(240, 67, 26))
                    linear_gradient.setColorAt(1, QtGui.QColor(255, 122, 53))
                    painter.setBrush(QtGui.QBrush(linear_gradient))
                painter.drawEllipse(
                    pos_x + (x_padding * i),
                    self.ui.frm_box.height() / 2 + 10,
                    15, 15)

            painter.end()
        return False

    def showEvent(self, event):
        """Start the dot animation."""
        self.ui.frm_box.installEventFilter(self)
        palette = QtGui.QPalette(self.palette())
        palette.setColor(palette.Background, QtCore.Qt.transparent)
        self.setPalette(palette)

        if not self.timer:
            self.timer = self.startTimer(200)

    def timerEvent(self, event):
        """Execute a loop to update the dot animation."""
        if self.counter in (0, 4):
            self.orientation = not self.orientation
        if self.orientation:
            self.counter += 1
        else:
            self.counter -= 1
        self.update()

    # pylint: enable=C0103
