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
"""Page to allow the user to login into Ubuntu Single Sign On."""

from functools import partial

from PyQt4 import QtGui, QtCore

from ubuntu_sso import NO_OP
from ubuntu_sso.logger import setup_gui_logging
from ubuntu_sso.qt import LINK_STYLE, build_general_error_message
from ubuntu_sso.qt.sso_wizard_page import SSOWizardPage
from ubuntu_sso.qt.ui.current_user_sign_in_ui import Ui_CurrentUserSignInPage
from ubuntu_sso.utils import compat
from ubuntu_sso.utils.ui import (
    CANCEL_BUTTON,
    CREATE_ACCOUNT_LABEL,
    EMAIL_LABEL,
    FORGOTTEN_PASSWORD_BUTTON,
    is_correct_email,
    LOGIN_PASSWORD_LABEL,
    LOGIN_TITLE,
    LOGIN_SUBTITLE,
    SIGN_IN_BUTTON,
)


logger = setup_gui_logging('ubuntu_sso.current_user_sign_in_page')


class CurrentUserSignInPage(SSOWizardPage):
    """Wizard Page that lets a current user Sign into Ubuntu Single Sign On."""

    ui_class = Ui_CurrentUserSignInPage
    userLoggedIn = QtCore.pyqtSignal(compat.text_type)
    passwordForgotten = QtCore.pyqtSignal()
    createAccount = QtCore.pyqtSignal()
    userNotValidated = QtCore.pyqtSignal(compat.text_type)

    @property
    def _signals(self):
        """The signals to connect to the backend."""
        result = {'LoggedIn':
                      self._filter_by_app_name(self.on_logged_in),
                  'LoginError':
                      self._filter_by_app_name(self.on_login_error),
                  'UserNotValidated':
                      self._filter_by_app_name(self.on_user_not_validated),
                  }
        return result

    @property
    def password(self):
        """Return the content of the password edit."""
        return compat.text_type(self.ui.password_edit.text())

    def on_user_not_validated(self, app_name, email):
        """Show the validate email page."""
        self.hide_overlay()
        email = compat.text_type(self.ui.email_edit.text())
        self.userNotValidated.emit(email)

    # Invalid names of Qt-inherited methods
    # pylint: disable=C0103

    def nextId(self):
        """Provide the next id."""
        return self.next

    def initializePage(self):
        """Setup UI details."""
        logger.debug('initializePage - About to show CurrentUserSignInPage')
        self.setButtonText(QtGui.QWizard.CancelButton, CANCEL_BUTTON)
        # Layout without custom button 1,
        # without finish button
        self.wizard().setButtonLayout([])

        # Set sign_in_button as default when the page is shown.
        self.ui.sign_in_button.setDefault(True)
        self.ui.sign_in_button.setEnabled(False)

    def cleanupPage(self):
        """Reset the wizard buttons."""
        super(CurrentUserSignInPage, self).cleanupPage()
        self.wizard().setButtonLayout([QtGui.QWizard.Stretch])

    def _set_translated_strings(self):
        """Set the translated strings."""
        self.setTitle(LOGIN_TITLE.format(app_name=self.app_name))
        self.setSubTitle(LOGIN_SUBTITLE % {'app_name': self.app_name})
        self.ui.email_label.setText(EMAIL_LABEL)
        self.ui.password_label.setText(LOGIN_PASSWORD_LABEL)
        forgotten_text = LINK_STYLE.format(link_url='#',
                            link_text=FORGOTTEN_PASSWORD_BUTTON)
        self.ui.forgot_password_label.setText(forgotten_text)
        link_text = CREATE_ACCOUNT_LABEL.format(app_name=self.app_name)
        account_text = LINK_STYLE.format(link_url='#', link_text=link_text)
        self.ui.create_account_label.setText(account_text)
        self.ui.sign_in_button.setText(SIGN_IN_BUTTON)

    def _connect_ui(self):
        """Connect the buttons to perform actions."""
        self.ui.forgot_password_label.linkActivated.connect(
                                                    self.on_forgotten_password)
        self.ui.create_account_label.linkActivated.connect(
                                                    self.on_create_account)
        self.ui.email_edit.textChanged.connect(self._validate)
        self.ui.password_edit.textChanged.connect(self._validate)
        self.ui.sign_in_button.clicked.connect(self.login)

    def _validate(self):
        """Perform input validation."""
        correct_mail = is_correct_email(
                        compat.text_type(self.ui.email_edit.text()))
        correct_password = len(
                        compat.text_type(self.ui.password_edit.text())) > 0
        enabled = correct_mail and correct_password
        self.ui.sign_in_button.setEnabled(enabled)

    def login(self):
        """Perform the login using the self.backend."""
        # grab the data from the view and call the backend
        email = compat.text_type(self.ui.email_edit.text())
        logger.info('CurrentUserSignInPage.login for: %s', email)
        password = compat.text_type(self.ui.password_edit.text())
        args = (self.app_name, email, password)
        if self.ping_url:
            f = self.backend.login_and_ping
            args = args + (self.ping_url,)
        else:
            f = self.backend.login

        self.hide_error()
        self.show_overlay()
        error_handler = partial(self._handle_error, f, self.on_login_error)
        f(*args, reply_handler=NO_OP, error_handler=error_handler)

    def on_login_error(self, app_name, error):
        """There was an error when login in."""
        # let the user know
        logger.error('Got error when login %s, error: %s',
            self.app_name, error)
        self.show_error(build_general_error_message(error))

    def on_logged_in(self, app_name, result):
        """We managed to log in."""
        logger.info('Logged in for %s', app_name)
        self.hide_overlay()
        email = compat.text_type(self.ui.email_edit.text())
        logger.debug('About to emit userLoggedIn signal with: (%s).', email)
        self.userLoggedIn.emit(email)

    def on_forgotten_password(self, link=None):
        """Show the user the forgotten password page."""
        self.hide_overlay()
        logger.debug('About to emit passwordForgotten signal')
        self.passwordForgotten.emit()

    def on_create_account(self, link=None):
        """Show the user the account creation page."""
        self.hide_overlay()
        logger.debug('About to emit createAccount signal')
        self.createAccount.emit()
