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
"""Pages from SSO."""

from twisted.internet import defer
from PyQt4 import QtGui, QtCore

from ubuntu_sso import networkstate
from ubuntu_sso.logger import setup_logging
from ubuntu_sso.qt.sso_wizard_page import SSOWizardPage
from ubuntu_sso.qt.ui import network_detection_ui
from ubuntu_sso.utils.ui import (
    CLOSE_AND_SETUP_LATER,
    NETWORK_DETECTION_TITLE,
    NETWORK_DETECTION_WARNING,
    TRY_AGAIN_BUTTON,
)


logger = setup_logging('ubuntu_sso.network_detection_page')


class NetworkDetectionPage(SSOWizardPage):

    """Widget to show if we don't detect a network connection."""

    ui_class = network_detection_ui.Ui_Form
    connectionDetected = QtCore.pyqtSignal()

    def __init__(self, *args, **kwargs):
        super(NetworkDetectionPage, self).__init__(*args, **kwargs)
        banner_pixmap = kwargs.pop('banner_pixmap', None)
        if banner_pixmap is not None:
            self.ui.image_label.setPixmap(banner_pixmap)
        self.btn_try_again = None

    # pylint: disable=C0103

    def initializePage(self):
        """Set UI details."""
        logger.debug('initializePage - About to show NetworkDetectionPage')
        self.wizard()._next_id = -1

        self.setButtonText(QtGui.QWizard.CustomButton1, TRY_AGAIN_BUTTON)
        self.setButtonText(QtGui.QWizard.CancelButton,
            CLOSE_AND_SETUP_LATER)
        self.wizard().setButtonLayout([QtGui.QWizard.Stretch,
                                       QtGui.QWizard.CustomButton1,
                                       QtGui.QWizard.CancelButton,
                                       ])

        try:
            self.wizard().customButtonClicked.disconnect()
        except TypeError:
            pass

        self.ui.label.setText(NETWORK_DETECTION_WARNING %
                              {'app_name': self.app_name})
        self.btn_try_again = self.wizard().button(QtGui.QWizard.CustomButton1)
        self.btn_try_again.setDefault(True)
        self.wizard().customButtonClicked.connect(self.try_again)

    # pylint: enable=C0103

    @defer.inlineCallbacks
    def try_again(self, button_id=QtGui.QWizard.CustomButton1):
        """Test the connection again."""
        if button_id == QtGui.QWizard.CustomButton1:
            d = yield networkstate.is_machine_connected()
            if d:
                self.connectionDetected.emit()

    def _set_translated_strings(self):
        """Implement in each child."""
        self.setTitle(NETWORK_DETECTION_TITLE)

    def _connect_ui(self):
        """Implement in each child."""
