# -*- coding: utf-8 -*-
#
# Copyright 2011-2013 Canonical Ltd.
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
"""Qt implementation of the UI."""

from functools import wraps

# pylint: disable=F0401,E0611
from PyQt4.QtCore import Qt, pyqtSignal
from PyQt4.QtGui import (
    QApplication,
    QCursor,
    QFrame,
    QHBoxLayout,
    QLabel,
    QStyle,
    QVBoxLayout,
    QWizardPage,
)
from twisted.internet import defer

from ubuntu_sso import main
from ubuntu_sso.constants import APP_NAME, TC_URL, POLICY_URL, PING_URL
from ubuntu_sso.logger import setup_gui_logging, log_call
from ubuntu_sso.qt import (
    ERROR_STYLE,
    maybe_elide_text,
    PREFERED_UI_SIZE,
    TITLE_STYLE,
)
from ubuntu_sso.utils.ui import GENERIC_BACKEND_ERROR


logger = setup_gui_logging('ubuntu_sso.sso_wizard_page')


class WizardHeader(QFrame):
    """WizardHeader Class for Title and Subtitle in all wizard pages."""

    def __init__(self, max_width, parent=None):
        """Create a new instance."""
        super(WizardHeader, self).__init__(parent=parent)
        self.max_width = max_width
        self.max_title_width = self.max_width * 0.95
        self.max_subtitle_width = self.max_width * 1.8

        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(0, 0, 0, 0)
        self.title_label = QLabel()
        self.title_label.setWordWrap(True)
        self.title_label.setObjectName('title_label')
        self.subtitle_label = QLabel()
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setFixedHeight(32)
        vbox.addWidget(self.title_label)
        vbox.addWidget(self.subtitle_label)
        self.title_label.setVisible(False)
        self.subtitle_label.setVisible(False)

    def set_title(self, title):
        """Set the Title of the page or hide it otherwise"""
        if title:
            maybe_elide_text(self.title_label, title, self.max_title_width,
                             markup=TITLE_STYLE)
            self.title_label.setVisible(True)
        else:
            self.title_label.setVisible(False)

    def set_subtitle(self, subtitle):
        """Set the Subtitle of the page or hide it otherwise"""
        if subtitle:
            maybe_elide_text(self.subtitle_label, subtitle,
                             self.max_subtitle_width)
            self.subtitle_label.setVisible(True)
        else:
            self.subtitle_label.setVisible(False)


class BaseWizardPage(QWizardPage):
    """Base class for all wizard pages."""

    ui_class = None
    max_width = 0
    processingStarted = pyqtSignal()
    processingFinished = pyqtSignal()

    def __init__(self, parent=None):
        super(BaseWizardPage, self).__init__(parent=parent)

        self.ui = None
        if self.ui_class is not None:
            # self.ui_class is not callable, pylint: disable=E1102
            self.ui = self.ui_class()
            self.ui.setupUi(self)

        if self.layout() is None:
            self.setLayout(QVBoxLayout(self))

        # Set the error area
        self.form_errors_label = QLabel()
        self.form_errors_label.setObjectName('form_errors')
        self.form_errors_label.setAlignment(Qt.AlignBottom)
        self.layout().insertWidget(0, self.form_errors_label)

        # Set the header
        self.header = WizardHeader(max_width=self.max_width)
        self.header.set_title(title='')
        self.header.set_subtitle(subtitle='')
        self.layout().insertWidget(0, self.header)

        self.layout().setAlignment(Qt.AlignLeft)

        self._is_processing = False

    def _get_is_processing(self):
        """Is this widget processing any request?"""
        return self._is_processing

    def _set_is_processing(self, new_value):
        """Set this widget to be processing a request."""
        self._is_processing = new_value
        self.setEnabled(not new_value)
        if not self._is_processing:
            self.processingFinished.emit()
        else:
            self.processingStarted.emit()

    is_processing = property(fget=_get_is_processing, fset=_set_is_processing)

    # pylint: disable=C0103

    def cleanupPage(self):
        """Hide the errors."""
        self.hide_error()

    def setTitle(self, title=''):
        """Set the Wizard Page Title."""
        self.header.set_title(title)

    def setSubTitle(self, subtitle=''):
        """Set the Wizard Page Subtitle."""
        self.header.set_subtitle(subtitle)

    def title(self):
        """Return the header's title."""
        return self.header.title_label.text()

    def subTitle(self):
        """Return the header's subtitle."""
        return self.header.subtitle_label.text()

    # pylint: enable=C0103

    @log_call(logger.error)
    def show_error(self, message):
        """Show an error message inside the page."""
        self.is_processing = False
        maybe_elide_text(self.form_errors_label, message,
                         self.max_width * 0.95, markup=ERROR_STYLE)

    def hide_error(self):
        """Hide the label errors in the current page."""
        # We actually want the label with one empty char, because if it is an
        # empty string, the height of the label is 0
        self.form_errors_label.setText(' ')


class SSOWizardPage(BaseWizardPage):
    """Root class for all SSO specific wizard pages."""

    _signals = {}  # override in children
    max_width = PREFERED_UI_SIZE['width']

    def __init__(self, app_name, **kwargs):
        """Create a new instance."""
        parent = kwargs.pop('parent', None)
        super(SSOWizardPage, self).__init__(parent=parent)

        # store common useful data provided by the app
        self.app_name = APP_NAME
        self.ping_url = PING_URL
        self.tc_url = TC_URL
        self.policy_url = POLICY_URL
        self.help_text = kwargs.get('help_text', '')

        self._signals_receivers = {}
        self.backend = None

        self.setup_page()

    def hide_overlay(self):
        """Emit the signal to notify the upper container that ends loading."""
        self.is_processing = False

    def show_overlay(self):
        """Emit the signal to notify the upper container that is loading."""
        self.is_processing = True

    @defer.inlineCallbacks
    def setup_page(self):
        """Setup the widget components."""
        logger.info('Starting setup_page for: %r', self)
        # pylint: disable=W0702,W0703
        try:
            # Get Backend
            client = yield main.get_sso_client()
            self.backend = client.sso_login
            self._set_translated_strings()
            self._connect_ui()
            # Call _setup_signals at the end, so we ensure that the UI
            # is at least styled as expected if the operations with the
            # backend fails.
            self._setup_signals()
        except:
            message = 'There was a problem trying to setup the page %r' % self
            self.show_error(message)
            logger.exception(message)
            self.setEnabled(False)
        # pylint: enable=W0702,W0703
        logger.info('%r - setup_page ends, backend is %r.', self, self.backend)

    def _filter_by_app_name(self, f):
        """Excecute the decorated function only for 'self.app_name'."""

        @wraps(f)
        def inner(app_name, *args, **kwargs):
            """Execute 'f' only if 'app_name' matches 'self.app_name'."""
            result = None
            if app_name == self.app_name:
                result = f(app_name, *args, **kwargs)
            else:
                logger.info('%s: ignoring call since received app_name '
                            '"%s" (expected "%s")',
                            f.__name__, app_name, self.app_name)
            return result

        return inner

    def _setup_signals(self):
        """Bind signals to callbacks to be able to test the pages."""
        for signal, method in self._signals.items():
            actual = self._signals_receivers.get(signal)
            if actual is not None:
                msg = 'Signal %r is already connected with %r.'
                logger.warning(msg, signal, actual)

            match = self.backend.connect_to_signal(signal, method)
            self._signals_receivers[signal] = match

    def _set_translated_strings(self):
        """Implement in each child."""

    def _connect_ui(self):
        """Implement in each child."""

    def _handle_error(self, remote_call, handler, error):
        """Handle any error when calling the remote backend."""
        logger.error('Remote call %r failed with: %r', remote_call, error)
        errordict = {'message': GENERIC_BACKEND_ERROR}
        handler(self.app_name, errordict)


class EnhancedLineEdit(object):
    """Represents and enhanced lineedit.

    This class works on an already added lineedit to the widget so
    that we are just adding extra items to it.
    """

    def __init__(self, line_edit, valid_cb=lambda x: False,
                 warning_sign=False):
        """Create an instance."""
        super(EnhancedLineEdit, self).__init__()
        self._line_edit = line_edit
        layout = QHBoxLayout(self._line_edit)
        layout.setMargin(0)
        self._line_edit.setLayout(layout)
        self.valid_cb = valid_cb
        layout.addStretch()
        self.clear_label = QLabel(self._line_edit)
        self.clear_label.setMargin(2)
        self.clear_label.setProperty("lineEditWarning", True)
        layout.addWidget(self.clear_label)
        self.clear_label.setMinimumSize(16, 16)
        self.clear_label.setVisible(False)
        self.clear_label.setCursor(QCursor(Qt.ArrowCursor))
        if warning_sign:
            icon = QApplication.style().standardIcon(
                QStyle.SP_MessageBoxWarning)
            self.clear_label.setPixmap(icon.pixmap(16, 16))
        # connect the change of text to the cation that will check if the
        # text is valid and if the icon should be shown.
        self._line_edit.textChanged.connect(self.show_button)

    def show_button(self, string):
        """Decide if we show the button or not."""
        if not self.valid_cb(string) and self.clear_label.pixmap() is not None:
            self.clear_label.setVisible(True)
        else:
            self.clear_label.setVisible(False)


class SSOWizardEnhancedEditPage(SSOWizardPage):
    """Page that contains enhanced line edits."""

    # Method '_connect_ui', '_set_translated_strings' is abstract in class
    # 'SSOWizardPage' but is not overridden
    # pylint: disable=W0223

    def __init__(self, *args, **kwargs):
        """Create a new instance."""
        self._enhanced_edits = {}
        super(SSOWizardEnhancedEditPage, self).__init__(*args, **kwargs)

    def set_line_edit_validation_rule(self, edit, cb):
        """Set a new enhanced edit so that we can show an icon."""
        if edit in self._enhanced_edits:
            self._enhanced_edits[edit].valid_cb = cb
        else:
            # create a new enhanced edit
            enhanced_edit = EnhancedLineEdit(edit, cb)
            self._enhanced_edits[edit] = enhanced_edit
