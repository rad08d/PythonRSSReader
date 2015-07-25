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
"""SSO Wizard UI."""

import sys

from PyQt4.QtCore import pyqtSignal
from PyQt4.QtGui import (
    QFrame,
    QVBoxLayout,
    QWizard,
)
from twisted.internet import defer

from ubuntu_sso import (
    networkstate,
    USER_CANCELLATION,
    USER_SUCCESS,
)
from ubuntu_sso.logger import setup_gui_logging
from ubuntu_sso.utils import compat
from ubuntu_sso.qt import PREFERED_UI_SIZE, WINDOW_TITLE
from ubuntu_sso.qt.current_user_sign_in_page import CurrentUserSignInPage
from ubuntu_sso.qt.email_verification_page import EmailVerificationPage
from ubuntu_sso.qt.error_page import ErrorPage
from ubuntu_sso.qt.forgotten_password_page import ForgottenPasswordPage
from ubuntu_sso.qt.loadingoverlay import LoadingOverlay
from ubuntu_sso.qt.network_detection_page import NetworkDetectionPage
from ubuntu_sso.qt.reset_password_page import ResetPasswordPage
from ubuntu_sso.qt.setup_account_page import SetupAccountPage
from ubuntu_sso.qt.success_page import SuccessPage

logger = setup_gui_logging('ubuntu_sso.gui')


class UbuntuSSOWizard(QWizard):
    """Wizard used to create or use sso."""

    # definition of the signals raised by the widget
    recoverableError = pyqtSignal('QString', 'QString')
    loginSuccess = pyqtSignal('QString', 'QString')
    registrationSuccess = pyqtSignal('QString', 'QString')

    def __init__(self, app_name, **kwargs):
        """Create a new wizard."""
        logger.debug('UbuntuSSOWizard: app_name %r, kwargs %r.',
                     app_name, kwargs)
        parent = kwargs.pop('parent', None)
        super(UbuntuSSOWizard, self).__init__(parent=parent)
        self.overlay = LoadingOverlay(self)
        self.overlay.hide()
        self._next_id = -1
        self.setOption(QWizard.HaveFinishButtonOnEarlyPages, True)
        self.setOption(QWizard.NoBackButtonOnStartPage, True)
        self.exit_code = USER_CANCELLATION

        self.app_name = app_name
        self.login_only = kwargs.pop('login_only', False)
        self.close_callback = kwargs.pop('close_callback', lambda: None)

        # store the ids of the pages so that it is easier to access them later
        self._pages = {}

        # prepare kwargs to be suitable for the pages
        kwargs['app_name'] = self.app_name
        kwargs['parent'] = self

        self.network_page = NetworkDetectionPage(self.app_name)
        self.network_page.connectionDetected.connect(self._connection_detected)
        self.addPage(self.network_page)

        # set the diff pages of the QWizard
        self.setup_account = SetupAccountPage(**kwargs)
        self.setup_account.userRegistered.connect(
            self._move_to_email_verification_page)
        # There are no tests for signal connections on
        # this file (LP:1046886)
        self.setup_account.signIn.connect(self._move_to_login_page)
        self.addPage(self.setup_account)

        self.current_user = CurrentUserSignInPage(**kwargs)
        self.current_user.userNotValidated.connect(
            self._move_to_email_verification_page)
        self.current_user.userLoggedIn.connect(self._move_to_success_page)
        self.current_user.passwordForgotten.connect(
            self._move_to_forgotten_page)
        self.current_user.createAccount.connect(
            self._move_to_setup_account_page)
        self.addPage(self.current_user)

        self.email_verification = EmailVerificationPage(**kwargs)
        self.email_verification.registrationSuccess.connect(
            self._move_to_success_page)
        self.addPage(self.email_verification)

        self.success = SuccessPage(**kwargs)
        self.addPage(self.success)

        self.error = ErrorPage(**kwargs)
        self.addPage(self.error)

        self.forgotten = ForgottenPasswordPage(**kwargs)
        self.forgotten.passwordResetTokenSent.connect(
            self._move_to_reset_password_page)
        self.addPage(self.forgotten)

        self.reset_password = ResetPasswordPage(**kwargs)
        back = lambda *a: self._go_back_to_page(self.current_user)
        self.reset_password.passwordChanged.connect(back)
        self.addPage(self.reset_password)

        # set the buttons layout to only have cancel and back since the next
        # buttons are the ones used in the diff pages.
        buttons_layout = []
        buttons_layout.append(QWizard.Stretch)
        buttons_layout.append(QWizard.BackButton)
        buttons_layout.append(QWizard.CancelButton)
        self.setButtonLayout(buttons_layout)
        self.setWindowTitle(self.app_name)
        self.setWizardStyle(QWizard.ModernStyle)
        self.button(QWizard.CancelButton).clicked.connect(self.close)
        self.setMinimumSize(PREFERED_UI_SIZE['width'],
            PREFERED_UI_SIZE['height'])

        # This is missing tests (LP:1046887)
        if self.login_only:
            self._move_to_login_page()
        else:
            self._move_to_setup_account_page()

    @defer.inlineCallbacks
    def check_network_connection(self):
        """Check if the NetworkDetectionPage is needed to be shown."""
        d = yield networkstate.is_machine_connected()
        if d:
            self._connection_detected()

    def _connection_detected(self):
        """Connection restablished, move to the proper page."""
        if self.login_only:
            self._next_id = self.current_user_page_id
        else:
            self._next_id = self.setup_account_page_id
        self.next()
        self._next_id = -1

    # pylint: disable=C0103

    def showEvent(self, event):
        """Check the network connection before the ui is shown."""
        super(UbuntuSSOWizard, self).showEvent(event)
        self.check_network_connection()

    def nextId(self):
        """Return the id of the next page."""
        return self._next_id

    def addPage(self, page):
        """Add 'page' to this wizard."""
        page_id = super(UbuntuSSOWizard, self).addPage(page)
        page.processingStarted.connect(self.overlay.show)
        page.processingFinished.connect(self.overlay.hide)
        self._pages[page] = page_id

    # pylint: enable=C0103

    def _go_back_to_page(self, page):
        """Move back until it reaches the 'page'."""
        logger.debug('Moving back from page: %s, to page: %s',
            self.currentPage(), page)
        page_id = self._pages[page]
        visited_pages = self.visitedPages()
        for index in reversed(visited_pages):
            if index == page_id:
                break
            self.back()

    def _move_to_reset_password_page(self):
        """Move to the reset password page wizard."""
        logger.debug('Moving to ResetPasswordPage from: %s',
            self.currentPage())
        self._next_id = self.reset_password_page_id
        self.next()
        self._next_id = -1

    def _move_to_email_verification_page(self, email):
        """Move to the email verification page wizard."""
        logger.debug('Moving to EmailVerificationPage from: %s',
            self.currentPage())
        self._next_id = self.email_verification_page_id
        self.email_verification.email = compat.text_type(email)
        self.email_verification.password = self.currentPage().password
        self.next()
        self._next_id = -1

    def _move_to_setup_account_page(self):
        """Move to the setup account page wizard."""
        logger.debug('Moving to SetupAccountPage from: %s',
            self.currentPage())
        self.setStartId(self.setup_account_page_id)
        self.restart()

    def _move_to_login_page(self):
        """Move to the login page wizard."""
        logger.debug('Moving to CurrentUserSignInPage from: %s',
            self.currentPage())
        self.setStartId(self.current_user_page_id)
        self.restart()

    def _move_to_success_page(self):
        """Move to the success page wizard."""
        logger.debug('Moving to SuccessPage from: %s',
            self.currentPage())
        self._next_id = self.success_page_id
        self.next()
        self.setButtonLayout([
            QWizard.Stretch,
            QWizard.FinishButton])
        self.button(QWizard.FinishButton).setEnabled(True)
        self.button(QWizard.FinishButton).setFocus()
        self.exit_code = USER_SUCCESS
        self._next_id = -1

    def _move_to_forgotten_page(self):
        """Move to the forgotten page wizard."""
        logger.debug('Moving to ForgottenPasswordPage from: %s',
            self.currentPage())
        self._next_id = self.forgotten_password_page_id
        self.next()
        self._next_id = -1

    @property
    def setup_account_page_id(self):
        """Return the id of the page used for sign in."""
        return self._pages[self.setup_account]

    @property
    def email_verification_page_id(self):
        """Return the id of the verification page."""
        return self._pages[self.email_verification]

    @property
    def current_user_page_id(self):
        """Return the id used to signin by a current user."""
        return self._pages[self.current_user]

    @property
    def success_page_id(self):
        """Return the id of the success page."""
        return self._pages[self.success]

    @property
    def forgotten_password_page_id(self):
        """Return the id of the forgotten password page."""
        return self._pages[self.forgotten]

    @property
    def reset_password_page_id(self):
        """Return the id of the reset password page."""
        return self._pages[self.reset_password]

    @property
    def error_page_id(self):
        """Return the id of the error page."""
        return self._pages[self.error]

    def done(self, result):
        """Replace the done method from the wizard."""
        self.closeEvent(None)

    # pylint: disable=C0103

    def closeEvent(self, event):
        """Catch close event and send the proper return code."""
        if self.parent() is not None:
            self.parent().close()
        else:
            sys.exit(self.exit_code)

    def resizeEvent(self, event):
        """Resize the overlay to fit all the widget."""
        super(UbuntuSSOWizard, self).resizeEvent(event)
        self.overlay.resize(event.size())

    # pylint: enable=C0103


class UbuntuSSOClientGUI(QFrame):
    """Ubuntu single sign-on GUI."""

    def __init__(self, app_name, **kwargs):
        """Create a new instance."""
        super(UbuntuSSOClientGUI, self).__init__()
        self.setObjectName("ubuntussoframe")
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(0, 0, 0, 0)
        logger.debug('UbuntuSSOClientGUI: app_name %r, kwargs %r.',
                     app_name, kwargs)
        self.app_name = app_name
        self.setWindowTitle(WINDOW_TITLE)
        # create the controller and the ui, then set the cb and call the show
        # method so that we can work
        self.wizard = UbuntuSSOWizard(app_name=app_name, **kwargs)
        vbox.addWidget(self.wizard)

    # pylint: disable=C0103

    def closeEvent(self, event):
        """Catch close event and send the proper return code."""
        sys.exit(self.wizard.exit_code)

    # pylint: enable=C0103
