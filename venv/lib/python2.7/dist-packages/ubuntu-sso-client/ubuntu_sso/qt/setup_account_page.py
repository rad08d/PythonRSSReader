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
"""Customized Setup Account page for SSO."""

import tempfile
import os
from io import BytesIO
from functools import partial

# pylint: disable=F0401
try:
    from PIL import Image
except ImportError:
    import Image
# pylint: enable=F0401

from PyQt4 import QtGui, QtCore

from ubuntu_sso import NO_OP
from ubuntu_sso.logger import setup_gui_logging, log_call
from ubuntu_sso.qt import (
    LINK_STYLE,
    build_general_error_message,
    common,
    enhanced_check_box,
    ERROR_STYLE,
)
from ubuntu_sso.qt.sso_wizard_page import SSOWizardEnhancedEditPage
from ubuntu_sso.qt.ui.setup_account_ui import Ui_SetUpAccountPage
from ubuntu_sso.utils import compat
from ubuntu_sso.utils.ui import (
    AGREE_TO_PRIVACY_POLICY,
    AGREE_TO_TERMS,
    AGREE_TO_TERMS_AND_PRIVACY_POLICY,
    CAPTCHA_LOAD_ERROR,
    CAPTCHA_RELOAD_MESSAGE,
    CAPTCHA_RELOAD_TEXT,
    CAPTCHA_REQUIRED_ERROR,
    CAPTCHA_SOLUTION_ENTRY,
    EMAIL,
    EMAIL1_ENTRY,
    EMAIL2_ENTRY,
    EMAIL_INVALID,
    EMAIL_MATCH,
    EMAIL_MISMATCH,
    EMPTY_NAME,
    INVALID_EMAIL,
    is_min_required_password,
    is_correct_email,
    JOIN_HEADER_LABEL,
    NAME_ENTRY,
    NAME_INVALID,
    PASSWORD,
    PASSWORD1_ENTRY,
    PASSWORD2_ENTRY,
    PASSWORD_HELP,
    PASSWORD_MISMATCH,
    PASSWORD_TOO_WEAK,
    PRIVACY_POLICY_TEXT,
    RETYPE_EMAIL,
    RETYPE_PASSWORD,
    SET_UP_ACCOUNT_BUTTON,
    SIGN_IN_LABEL,
    TERMS_TEXT,
    REGISTER_TITLE,
)


logger = setup_gui_logging('ubuntu_sso.setup_account_page')

ERROR_EMAIL = 'email'


class SetupAccountPage(SSOWizardEnhancedEditPage):
    """Customized Setup Account page for SSO."""

    ui_class = Ui_SetUpAccountPage
    userRegistered = QtCore.pyqtSignal(compat.text_type)
    signIn = QtCore.pyqtSignal()

    def __init__(self, *args, **kwargs):
        self.captcha_file = None
        self.captcha_id = None
        self.captcha_received = False
        self.set_up_button = None
        self.terms_checkbox = None
        super(SetupAccountPage, self).__init__(*args, **kwargs)

    @property
    def _signals(self):
        """The signals to connect to the backend."""
        result = {
            'CaptchaGenerated':
                self._filter_by_app_name(self.on_captcha_generated),
            'CaptchaGenerationError':
                self._filter_by_app_name(self.on_captcha_generation_error),
            'UserRegistered':
                self._filter_by_app_name(self.on_user_registered),
            'UserRegistrationError':
                self._filter_by_app_name(self.on_user_registration_error),
        }
        return result

    @property
    def password(self):
        """Return the content of the password edit."""
        return compat.text_type(self.ui.password_edit.text())

    # Invalid name "initializePage"
    # pylint: disable=C0103

    def initializePage(self):
        """Setup UI details."""
        logger.debug('initializePage - About to show SetupAccountPage')
        # Set Setup Account button
        self.wizard().setOption(QtGui.QWizard.HaveCustomButton3, True)
        try:
            self.wizard().customButtonClicked.disconnect()
        except TypeError:
            pass
        self.setButtonText(QtGui.QWizard.CustomButton3, SET_UP_ACCOUNT_BUTTON)
        self.set_up_button = self.wizard().button(QtGui.QWizard.CustomButton3)
        self.set_up_button.clicked.connect(self.set_next_validation)
        self.set_up_button.setEnabled(False)

        self.ui.name_label.setText(NAME_ENTRY)
        self.ui.email_label.setText(EMAIL)
        self.ui.confirm_email_label.setText(RETYPE_EMAIL)
        self.ui.password_label.setText(PASSWORD)
        self.ui.confirm_password_label.setText(RETYPE_PASSWORD)

        # Button setup
        self.wizard().setButtonLayout([
            QtGui.QWizard.Stretch,
            QtGui.QWizard.CustomButton3])

        common.password_default_assistance(self.ui.password_assistance)
        # Hide assistance labels by default
        self.ui.name_assistance.setVisible(False)
        self.ui.email_assistance.setVisible(False)
        self.ui.confirm_email_assistance.setVisible(False)
        self.ui.password_assistance.setVisible(False)
        self.ui.refresh_label.setVisible(True)

    # pylint: enable=C0103

    def _set_translated_strings(self):
        """Set the strings."""
        # set the translated string
        title_page = REGISTER_TITLE.format(app_name=self.app_name)
        self.setTitle(title_page)
        self.setSubTitle(self.help_text)

        self.ui.name_label.setText(NAME_ENTRY)
        sign_in_link = LINK_STYLE.format(link_url='#',
            link_text=SIGN_IN_LABEL)
        self.ui.sign_in_label.setText(sign_in_link)
        self.ui.email_label.setText(EMAIL1_ENTRY)
        self.ui.confirm_email_label.setText(EMAIL2_ENTRY)
        self.ui.password_label.setText(PASSWORD1_ENTRY)
        self.ui.confirm_password_label.setText(PASSWORD2_ENTRY)
        self.ui.password_edit.setToolTip(PASSWORD_HELP)
        self.ui.captcha_solution_edit.setPlaceholderText(
            CAPTCHA_SOLUTION_ENTRY)
        link = LINK_STYLE.format(link_url='#', link_text=CAPTCHA_RELOAD_TEXT)
        self.ui.refresh_label.setText(CAPTCHA_RELOAD_MESSAGE %
                                      {'reload_link': link})

        if self.tc_url:
            terms_links = LINK_STYLE.format(link_url=self.tc_url,
                                            link_text=TERMS_TEXT)
        if self.policy_url:
            privacy_policy_link = LINK_STYLE.format(link_url=self.policy_url,
                                                 link_text=PRIVACY_POLICY_TEXT)

        terms = ''
        if self.tc_url and self.policy_url:
            terms = AGREE_TO_TERMS_AND_PRIVACY_POLICY.format(
                        app_name=self.app_name,
                        terms_and_conditions=terms_links,
                        privacy_policy=privacy_policy_link)
        elif self.tc_url:
            terms = AGREE_TO_TERMS.format(app_name=self.app_name,
                        terms_and_conditions=terms_links)
        elif self.policy_url:
            terms = AGREE_TO_PRIVACY_POLICY.format(app_name=self.app_name,
                        privacy_policy=privacy_policy_link)

        self.terms_checkbox = enhanced_check_box.EnhancedCheckBox(terms, self)
        self.ui.hlayout_check.addWidget(self.terms_checkbox)
        self.terms_checkbox.setVisible(bool(self.tc_url or self.policy_url))

        self._register_fields()

    def _set_line_edits_validations(self):
        """Set the validations to be performed on the edits."""
        logger.debug('SetUpAccountPage._set_line_edits_validations')
        self.set_line_edit_validation_rule(self.ui.email_edit,
                                                is_correct_email)
        # set the validation rule for the email confirmation
        self.set_line_edit_validation_rule(
                                        self.ui.confirm_email_edit,
                                        self.is_correct_email_confirmation)
        # connect the changed text of the password to trigger a changed text
        # in the confirm so that the validation is redone
        self.ui.email_edit.textChanged.connect(
                            self.ui.confirm_email_edit.textChanged.emit)
        self.set_line_edit_validation_rule(self.ui.password_edit,
                                                is_min_required_password)
        self.set_line_edit_validation_rule(
                                        self.ui.confirm_password_edit,
                                        self.is_correct_password_confirmation)
        # same as the above case, lets connect a signal to a signal
        self.ui.password_edit.textChanged.connect(
            self.ui.confirm_password_edit.textChanged.emit)

    def _connect_ui(self):
        """Set the connection of signals."""
        self._set_line_edits_validations()

        self.ui.captcha_view.setPixmap(QtGui.QPixmap())
        self.ui.password_edit.textEdited.connect(
            lambda: common.password_assistance(self.ui.password_edit,
                                                 self.ui.password_assistance,
                                                 common.NORMAL))

        self.ui.refresh_label.linkActivated.connect(self.hide_error)
        self.ui.refresh_label.linkActivated.connect(
            lambda url: self._refresh_captcha())
        # We need to check if we enable the button on many signals
        self.ui.name_edit.textEdited.connect(self._enable_setup_button)
        self.ui.email_edit.textEdited.connect(self._enable_setup_button)
        self.ui.confirm_email_edit.textEdited.connect(
            self._enable_setup_button)
        self.ui.password_edit.textEdited.connect(self._enable_setup_button)
        self.ui.confirm_password_edit.textEdited.connect(
            self._enable_setup_button)
        self.ui.captcha_solution_edit.textEdited.connect(
            self._enable_setup_button)
        self.terms_checkbox.stateChanged.connect(self._enable_setup_button)
        self.ui.sign_in_label.linkActivated.connect(self.signIn)

        self._refresh_captcha()

    def _enable_setup_button(self):
        """Only enable the setup button if the form is valid."""
        name = compat.text_type(self.ui.name_edit.text()).strip()
        email = compat.text_type(self.ui.email_edit.text())
        confirm_email = compat.text_type(self.ui.confirm_email_edit.text())
        password = compat.text_type(self.ui.password_edit.text())
        confirm_password = compat.text_type(
                self.ui.confirm_password_edit.text())
        captcha_solution = compat.text_type(
                self.ui.captcha_solution_edit.text())

        # Check for len(name) > 0 to ensure that a bool is assigned to enabled
        if not self.terms_checkbox.isVisible():
            checkbox_terms = True
        else:
            checkbox_terms = self.terms_checkbox.isChecked()

        enabled = checkbox_terms and \
          len(captcha_solution) > 0 and \
          is_min_required_password(password) and \
          password == confirm_password and is_correct_email(email) and \
          email == confirm_email and len(name) > 0

        self.set_up_button.setEnabled(enabled)

    def _refresh_captcha(self):
        """Refresh the captcha image shown in the ui."""
        logger.debug('SetUpAccountPage._refresh_captcha')
        # lets clean behind us, do we have the old file arround?
        if self.captcha_file and os.path.exists(self.captcha_file):
            os.unlink(self.captcha_file)
        fd = tempfile.NamedTemporaryFile()
        file_name = fd.name
        self.captcha_file = file_name
        args = (self.app_name, file_name)
        f = self.backend.generate_captcha
        error_handler = partial(self._handle_error, f,
            self.on_captcha_generation_error)
        f(*args, reply_handler=NO_OP, error_handler=error_handler)
        self.on_captcha_refreshing()

    def _set_titles(self):
        """Set the diff titles of the view."""
        logger.debug('SetUpAccountPage._set_titles')
        self.header.set_title(
            JOIN_HEADER_LABEL % {'app_name': self.app_name})
        self.header.set_subtitle(self._subtitle)

    def _register_fields(self):
        """Register the diff fields of the Ui."""
        self.registerField('email_address', self.ui.email_edit)
        self.registerField('password', self.ui.password_edit)

    @log_call(logger.debug)
    def on_captcha_generated(self, app_name, result):
        """A new image was generated."""
        self.captcha_id = result
        # HACK: First, let me apologize before hand, you can mention my mother
        # if needed I would do the same (mandel)
        # In an ideal world we could use the Qt plug-in for the images so that
        # we could load jpgs etc.. but this won't work when the app has been
        # brozen win py2exe using bundle_files=1
        # The main issue is that Qt will complain about the thread not being
        # the correct one when performing a moveToThread operation which is
        # done either by a setParent or something within the qtreactor, PIL
        # in this case does solve the issue. Sorry :(
        pil_image = Image.open(self.captcha_file)
        bytes_io = BytesIO()
        pil_image.save(bytes_io, format='png')
        pixmap_image = QtGui.QPixmap()
        pixmap_image.loadFromData(bytes_io.getvalue())
        self.captcha_image = pixmap_image
        self.on_captcha_refresh_complete()

    @log_call(logger.error)
    def on_captcha_generation_error(self, app_name, error):
        """An error ocurred."""
        self.show_error(CAPTCHA_LOAD_ERROR)
        self.on_captcha_refresh_complete()

    @log_call(logger.error)
    def on_user_registration_error(self, app_name, error):
        """Let the user know we could not register."""
        # errors are returned as a dict with the data we want to show.
        msg = error.pop(ERROR_EMAIL, '')
        if msg:
            self.set_error_message(self.ui.email_assistance, msg)
        error_msg = build_general_error_message(error)
        if error_msg:
            self.show_error(error_msg)
        self._refresh_captcha()

    @log_call(logger.info)
    def on_user_registered(self, app_name, email):
        """Execute when the user did register."""
        self.hide_overlay()
        email = compat.text_type(self.ui.email_edit.text())
        self.userRegistered.emit(email)

    def validate_form(self):
        """Validate the info of the form and return an error."""
        logger.debug('SetUpAccountPage.validate_form')
        name = compat.text_type(self.ui.name_edit.text()).strip()
        email = compat.text_type(self.ui.email_edit.text())
        confirm_email = compat.text_type(self.ui.confirm_email_edit.text())
        password = compat.text_type(self.ui.password_edit.text())
        confirm_password = compat.text_type(
                self.ui.confirm_password_edit.text())
        captcha_solution = compat.text_type(
                self.ui.captcha_solution_edit.text())
        condition = True
        messages = []
        if not name:
            condition = False
            self.set_error_message(self.ui.name_assistance,
                NAME_INVALID)
        if not is_correct_email(email):
            condition = False
            self.set_error_message(self.ui.email_assistance,
                EMAIL_INVALID)
        if email != confirm_email:
            condition = False
            self.set_error_message(self.ui.confirm_email_assistance,
                EMAIL_MISMATCH)
        if not is_min_required_password(password):
            messages.append(PASSWORD_TOO_WEAK)
        if password != confirm_password:
            messages.append(PASSWORD_MISMATCH)
        if not captcha_solution:
            messages.append(CAPTCHA_REQUIRED_ERROR)
        if len(messages) > 0:
            condition = False
            self.show_error('\n'.join(messages))
        return condition

    def set_next_validation(self):
        """Set the validation as the next page."""
        logger.debug('SetUpAccountPage.set_next_validation')
        email = compat.text_type(self.ui.email_edit.text())
        password = compat.text_type(self.ui.password_edit.text())
        name = compat.text_type(self.ui.name_edit.text())
        captcha_id = self.captcha_id
        captcha_solution = compat.text_type(
                self.ui.captcha_solution_edit.text())
        # validate the current info of the form, try to perform the action
        # to register the user, and then move foward
        if self.validate_form():
            self.show_overlay()
            self.hide_error()
            args = (self.app_name, email, password, name, captcha_id,
                captcha_solution)
            f = self.backend.register_user
            error_handler = partial(self._handle_error, f,
                self.on_user_registration_error)
            f(*args, reply_handler=NO_OP, error_handler=error_handler)

    def is_correct_email(self, email_address):
        """Return if the email is correct."""
        return '@' in email_address

    def is_correct_email_confirmation(self, email_address):
        """Return that the email is the same."""
        return compat.text_type(self.ui.email_edit.text()) == email_address

    def is_correct_password_confirmation(self, password):
        """Return that the passwords are correct."""
        return compat.text_type(self.ui.password_edit.text()) == password

    def focus_changed(self, old, now):
        """Check who has the focus to activate password popups if necessary."""
        if old == self.ui.name_edit:
            self.name_assistance()
        elif old == self.ui.email_edit:
            self.email_assistance()
        elif old == self.ui.confirm_email_edit:
            self.confirm_email_assistance()
        elif old == self.ui.confirm_password_edit:
            common.password_check_match(self.ui.password_edit,
                                      self.ui.confirm_password_edit,
                                      self.ui.password_assistance)
        if now == self.ui.password_edit:
            self.ui.password_assistance.setVisible(True)

    def name_assistance(self):
        """Show help for the name field."""
        text = compat.text_type(self.ui.name_edit.text())
        if not text.strip():
            self.set_error_message(self.ui.name_assistance,
                EMPTY_NAME)
            common.check_as_invalid(self.ui.name_edit)
        else:
            self.ui.name_assistance.setVisible(False)
            common.check_as_valid(self.ui.name_edit)

    def email_assistance(self):
        """Show help for the email field."""
        text = compat.text_type(self.ui.email_edit.text())
        if not is_correct_email(text):
            self.set_error_message(self.ui.email_assistance,
                INVALID_EMAIL)
            common.check_as_invalid(self.ui.email_edit)
        else:
            self.ui.email_assistance.setVisible(False)
            common.check_as_valid(self.ui.email_edit)

    def confirm_email_assistance(self):
        """Show help for the confirm email field."""
        text1 = compat.text_type(self.ui.email_edit.text())
        text2 = compat.text_type(self.ui.confirm_email_edit.text())
        if text1 != text2:
            self.set_error_message(self.ui.confirm_email_assistance,
                EMAIL_MATCH)
            common.check_as_invalid(self.ui.confirm_email_edit)
        else:
            self.ui.confirm_email_assistance.setVisible(False)
            common.check_as_valid(self.ui.confirm_email_edit)

    def set_error_message(self, label, msg):
        """Set the message to the proper label applying the error style."""
        label.setText(ERROR_STYLE % msg)
        label.setVisible(True)

    # pylint: disable=C0103

    def showEvent(self, event):
        """Set set_up_button as default button when the page is shown."""
        # This method should stays here because if we move it to initializePage
        # set_up_button won't take the proper style for hover and press
        if self.set_up_button is not None:
            self.set_up_button.setVisible(True)
            self.set_up_button.setDefault(True)
        self.connect(QtGui.QApplication.instance(),
            QtCore.SIGNAL("focusChanged(QWidget*, QWidget*)"),
            self.focus_changed)
        super(SetupAccountPage, self).showEvent(event)
        if not self.captcha_received:
            self.show_overlay()

    def hideEvent(self, event):
        """Disconnect the focusChanged signal when the page change."""
        if self.set_up_button is not None:
            self.set_up_button.setVisible(False)
        try:
            self.disconnect(QtGui.QApplication.instance(),
                QtCore.SIGNAL("focusChanged(QWidget*, QWidget*)"),
                self.focus_changed)
        except TypeError:
            pass
        super(SetupAccountPage, self).hideEvent(event)

    # pylint: enable=C0103

    def on_captcha_refreshing(self):
        """Show overlay when captcha is refreshing."""
        logger.info('SetUpAccountPage.on_captcha_refreshing')
        if self.isVisible():
            self.show_overlay()
        self.captcha_received = False

    def on_captcha_refresh_complete(self):
        """Hide overlay when captcha finished refreshing."""
        logger.info('SetUpAccountPage.on_captcha_refresh_complete')
        self.hide_overlay()
        self.captcha_received = True

    def get_captcha_image(self):
        """Return the path to the captcha image."""
        return self.ui.captcha_view.pixmap()

    def set_captcha_image(self, pixmap_image):
        """Set the new image of the captcha."""
        # lets set the QPixmap for the label
        self.ui.captcha_view.setPixmap(pixmap_image)

    captcha_image = property(get_captcha_image, set_captcha_image)
