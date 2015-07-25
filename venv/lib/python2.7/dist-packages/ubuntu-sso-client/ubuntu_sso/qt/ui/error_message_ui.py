# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'data/qt/error_message.ui'
#
# Created: Sat Apr  5 11:38:09 2014
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

class Ui_ErrorPage(object):
    def setupUi(self, ErrorPage):
        ErrorPage.setObjectName(_fromUtf8("ErrorPage"))
        ErrorPage.resize(400, 300)
        self.verticalLayout = QtGui.QVBoxLayout(ErrorPage)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.error_message_label = QtGui.QLabel(ErrorPage)
        self.error_message_label.setText(_fromUtf8("TextLabel"))
        self.error_message_label.setAlignment(QtCore.Qt.AlignCenter)
        self.error_message_label.setObjectName(_fromUtf8("error_message_label"))
        self.verticalLayout.addWidget(self.error_message_label)

        self.retranslateUi(ErrorPage)
        QtCore.QMetaObject.connectSlotsByName(ErrorPage)

    def retranslateUi(self, ErrorPage):
        pass

