# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'data/qt/email_verification.ui'
#
# Created: Sat Apr  5 11:38:08 2014
#      by: PyQt4 UI code generator 4.10.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_EmailVerificationPage(object):
    def setupUi(self, EmailVerificationPage):
        EmailVerificationPage.setObjectName(_fromUtf8("EmailVerificationPage"))
        EmailVerificationPage.resize(300, 148)
        EmailVerificationPage.setMinimumSize(QtCore.QSize(300, 0))
        self.verticalLayout_2 = QtGui.QVBoxLayout(EmailVerificationPage)
        self.verticalLayout_2.setSpacing(15)
        self.verticalLayout_2.setMargin(0)
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.verticalLayout = QtGui.QVBoxLayout()
        self.verticalLayout.setSpacing(3)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.label = QtGui.QLabel(EmailVerificationPage)
        self.label.setText(_fromUtf8("Verification code"))
        self.label.setObjectName(_fromUtf8("label"))
        self.verticalLayout.addWidget(self.label)
        self.verification_code_edit = QtGui.QLineEdit(EmailVerificationPage)
        self.verification_code_edit.setPlaceholderText(_fromUtf8(""))
        self.verification_code_edit.setObjectName(_fromUtf8("verification_code_edit"))
        self.verticalLayout.addWidget(self.verification_code_edit)
        self.verticalLayout_2.addLayout(self.verticalLayout)
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setObjectName(_fromUtf8("horizontalLayout_2"))
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem)
        self.next_button = QtGui.QPushButton(EmailVerificationPage)
        self.next_button.setText(_fromUtf8("Next"))
        self.next_button.setObjectName(_fromUtf8("next_button"))
        self.horizontalLayout_2.addWidget(self.next_button)
        self.verticalLayout_2.addLayout(self.horizontalLayout_2)
        spacerItem1 = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout_2.addItem(spacerItem1)

        self.retranslateUi(EmailVerificationPage)
        QtCore.QObject.connect(self.verification_code_edit, QtCore.SIGNAL(_fromUtf8("returnPressed()")), self.next_button.click)
        QtCore.QMetaObject.connectSlotsByName(EmailVerificationPage)

    def retranslateUi(self, EmailVerificationPage):
        pass

