# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'data/qt/current_user_sign_in.ui'
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

class Ui_CurrentUserSignInPage(object):
    def setupUi(self, CurrentUserSignInPage):
        CurrentUserSignInPage.setObjectName(_fromUtf8("CurrentUserSignInPage"))
        CurrentUserSignInPage.resize(302, 295)
        self.verticalLayout_2 = QtGui.QVBoxLayout(CurrentUserSignInPage)
        self.verticalLayout_2.setSpacing(15)
        self.verticalLayout_2.setMargin(0)
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.create_account_label = QtGui.QLabel(CurrentUserSignInPage)
        self.create_account_label.setObjectName(_fromUtf8("create_account_label"))
        self.verticalLayout_2.addWidget(self.create_account_label)
        self.verticalLayout = QtGui.QVBoxLayout()
        self.verticalLayout.setSpacing(3)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.email_label = QtGui.QLabel(CurrentUserSignInPage)
        self.email_label.setText(_fromUtf8("&Email"))
        self.email_label.setObjectName(_fromUtf8("email_label"))
        self.verticalLayout.addWidget(self.email_label)
        self.email_edit = QtGui.QLineEdit(CurrentUserSignInPage)
        self.email_edit.setMinimumSize(QtCore.QSize(300, 0))
        self.email_edit.setPlaceholderText(_fromUtf8(""))
        self.email_edit.setObjectName(_fromUtf8("email_edit"))
        self.verticalLayout.addWidget(self.email_edit)
        self.verticalLayout_2.addLayout(self.verticalLayout)
        self.verticalLayout_3 = QtGui.QVBoxLayout()
        self.verticalLayout_3.setSpacing(3)
        self.verticalLayout_3.setObjectName(_fromUtf8("verticalLayout_3"))
        self.password_label = QtGui.QLabel(CurrentUserSignInPage)
        self.password_label.setText(_fromUtf8("&Password"))
        self.password_label.setObjectName(_fromUtf8("password_label"))
        self.verticalLayout_3.addWidget(self.password_label)
        self.password_edit = QtGui.QLineEdit(CurrentUserSignInPage)
        self.password_edit.setMinimumSize(QtCore.QSize(300, 0))
        self.password_edit.setEchoMode(QtGui.QLineEdit.Password)
        self.password_edit.setPlaceholderText(_fromUtf8(""))
        self.password_edit.setObjectName(_fromUtf8("password_edit"))
        self.verticalLayout_3.addWidget(self.password_edit)
        self.verticalLayout_2.addLayout(self.verticalLayout_3)
        self.forgot_password_label = QtGui.QLabel(CurrentUserSignInPage)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.forgot_password_label.sizePolicy().hasHeightForWidth())
        self.forgot_password_label.setSizePolicy(sizePolicy)
        self.forgot_password_label.setText(_fromUtf8("Forgot password?"))
        self.forgot_password_label.setObjectName(_fromUtf8("forgot_password_label"))
        self.verticalLayout_2.addWidget(self.forgot_password_label)
        self.horizontalLayout_4 = QtGui.QHBoxLayout()
        self.horizontalLayout_4.setObjectName(_fromUtf8("horizontalLayout_4"))
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_4.addItem(spacerItem)
        self.sign_in_button = QtGui.QPushButton(CurrentUserSignInPage)
        self.sign_in_button.setEnabled(False)
        self.sign_in_button.setText(_fromUtf8("Sign In"))
        self.sign_in_button.setDefault(True)
        self.sign_in_button.setObjectName(_fromUtf8("sign_in_button"))
        self.horizontalLayout_4.addWidget(self.sign_in_button)
        self.verticalLayout_2.addLayout(self.horizontalLayout_4)
        spacerItem1 = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout_2.addItem(spacerItem1)
        self.email_label.setBuddy(self.email_edit)
        self.password_label.setBuddy(self.password_edit)

        self.retranslateUi(CurrentUserSignInPage)
        QtCore.QObject.connect(self.password_edit, QtCore.SIGNAL(_fromUtf8("returnPressed()")), self.sign_in_button.click)
        QtCore.QMetaObject.connectSlotsByName(CurrentUserSignInPage)

    def retranslateUi(self, CurrentUserSignInPage):
        self.create_account_label.setText(_translate("CurrentUserSignInPage", "Register with {app_name}.", None))

