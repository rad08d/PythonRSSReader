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
"""Reset Password page UI."""

from functools import partial

from PyQt4.QtCore import Qt, SIGNAL, pyqtSignal
from PyQt4.QtGui import QApplication

from ubuntu_sso import NO_OP
from ubuntu_sso.logger import setup_gui_logging
from ubuntu_sso.qt import build_general_error_message, common
from ubuntu_sso.qt.sso_wizard_page import SSOWizardEnhancedEditPage
from ubuntu_sso.qt.ui.reset_password_ui import Ui_ResetPasswordPage
from ubuntu_sso.utils import compat
from ubuntu_sso.utils.ui import (
    is_min_required_password,
    PASSWORD1_ENTRY,
    PASSWORD2_ENTRY,
    PASSWORD_HELP,
    RESET_CODE_ENTRY,
    RESET_PASSWORD,
    RESET_TITLE,
    RESET_SUBTITLE,
)


logger = setup_gui_logging('ubuntu_sso.reset_password_page')


class ResetPasswordPage(SSOWizardEnhancedEditPage):
    """Widget used to allow the user change his password."""

    ui_class = Ui_ResetPasswordPage
    passwordChanged = pyqtSignal(compat.text_type)

    @property
    def _signals(self):
        """The signals to connect to the backend."""
        result = {
            'PasswordChanged':
                self._filter_by_app_name(self.on_password_changed),
            'PasswordChangeError':
                self._filter_by_app_name(self.on_password_change_error),
        }
        return result

    def focus_changed(self, old, now):
        """Check who has the focus to activate password popups if necessary."""
        if now == self.ui.password_line_edit:
            self.ui.password_assistance.setVisible(True)
            common.password_default_assistance(self.ui.password_assistance)
        elif now == self.ui.confirm_password_line_edit:
            common.password_check_match(self.ui.password_line_edit,
                                      self.ui.confirm_password_line_edit,
                                      self.ui.password_assistance)

    # Invalid name "initializePage"
    # pylint: disable=C0103

    def initializePage(self):
        """Extends QWizardPage initializePage method."""
        logger.debug('initializePage - About to show ResetPasswordPage')
        super(ResetPasswordPage, self).initializePage()
        self.ui.gridLayout.setAlignment(Qt.AlignLeft)
        common.password_default_assistance(self.ui.password_assistance)
        self.ui.password_assistance.setVisible(False)
        self.setTitle(RESET_TITLE)
        self.setSubTitle(RESET_SUBTITLE)
        self.ui.password_label.setText(PASSWORD1_ENTRY)
        self.ui.confirm_password_label.setText(PASSWORD2_ENTRY)
        self.ui.reset_code.setText(RESET_CODE_ENTRY)

        self.ui.reset_password_button.setDefault(True)
        self.ui.reset_password_button.setEnabled(False)

    def showEvent(self, event):
        """Connect focusChanged signal from the application."""
        super(ResetPasswordPage, self).showEvent(event)
        self.connect(QApplication.instance(),
            SIGNAL("focusChanged(QWidget*, QWidget*)"),
            self.focus_changed)

    def hideEvent(self, event):
        """Disconnect the focusChanged signal when the page change."""
        super(ResetPasswordPage, self).hideEvent(event)
        try:
            self.disconnect(QApplication.instance(),
                SIGNAL("focusChanged(QWidget*, QWidget*)"),
                self.focus_changed)
        except TypeError:
            pass

    # pylint: enable=C0103

    def _set_translated_strings(self):
        """Translate the diff strings used in the app."""
        self.ui.reset_password_button.setText(RESET_PASSWORD)
        self.setSubTitle(PASSWORD_HELP)

    def _connect_ui(self):
        """Connect the different ui signals."""
        self.ui.password_line_edit.textEdited.connect(
            lambda: common.password_assistance(self.ui.password_line_edit,
                                                 self.ui.password_assistance,
                                                 common.NORMAL))
        self.ui.confirm_password_line_edit.textEdited.connect(
            lambda: common.password_check_match(self.ui.password_line_edit,
                                      self.ui.confirm_password_line_edit,
                                      self.ui.password_assistance))

        self.ui.reset_password_button.clicked.connect(
                                                    self.set_new_password)
        self.ui.reset_code_line_edit.textChanged.connect(self._validate)
        self.ui.password_line_edit.textChanged.connect(self._validate)
        self.ui.confirm_password_line_edit.textChanged.connect(
            self._validate)

        self._add_line_edits_validations()

    def _validate(self):
        """Enable the submit button if data is valid."""
        enabled = True
        code = compat.text_type(self.ui.reset_code_line_edit.text())
        password = compat.text_type(self.ui.password_line_edit.text())
        confirm_password = compat.text_type(
            self.ui.confirm_password_line_edit.text())
        if not is_min_required_password(password):
            enabled = False
        elif not self.is_correct_password_confirmation(confirm_password):
            enabled = False
        elif not code:
            enabled = False
        self.ui.reset_password_button.setEnabled(enabled)

    def _add_line_edits_validations(self):
        """Add the validations to be use by the line edits."""
        self.set_line_edit_validation_rule(
            self.ui.password_line_edit,
            is_min_required_password)
        self.set_line_edit_validation_rule(
            self.ui.confirm_password_line_edit,
            self.is_correct_password_confirmation)
        # same as the above case, lets connect a signal to a signal
        self.ui.password_line_edit.textChanged.connect(
            self.ui.confirm_password_line_edit.textChanged.emit)

    def on_password_changed(self, app_name, email):
        """Let user know that the password was changed."""
        logger.info('ResetPasswordPage.on_password_changed for %s, email: %s',
            app_name, email)
        self.hide_overlay()
        email = compat.text_type(
            self.wizard().forgotten.ui.email_line_edit.text())
        self.passwordChanged.emit(email)

    def on_password_change_error(self, app_name, error):
        """Let the user know that there was an error."""
        logger.error('Got error changing password for %s, error: %s',
                     self.app_name, error)
        self.show_error(build_general_error_message(error))

    def set_new_password(self):
        """Request a new password to be set."""
        self.hide_error()
        email = compat.text_type(
                    self.wizard().forgotten.ui.email_line_edit.text())
        code = compat.text_type(self.ui.reset_code_line_edit.text())
        password = compat.text_type(self.ui.password_line_edit.text())
        logger.info('Setting new password for %r and email %r with code %r',
                    self.app_name, email, code)
        args = (self.app_name, email, code, password)
        f = self.backend.set_new_password
        error_handler = partial(self._handle_error, f,
            self.on_password_change_error)
        self.show_overlay()
        f(*args, reply_handler=NO_OP, error_handler=error_handler)

    def is_correct_password_confirmation(self, password):
        """Return if the password is correct."""
        return compat.text_type(self.ui.password_line_edit.text()) == password
