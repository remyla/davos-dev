# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\styx\DEVSPACE\git\z2k-pipeline-toolkit\python\davos-dev\resources\ui\propertywidget.ui'
#
# Created: Thu Aug 20 09:19:51 2015
#      by: pyside-uic 0.2.14 running on PySide 1.2.0
#
# WARNING! All changes made in this file will be lost!

from PySide import QtCore, QtGui

class Ui_PropertyWidget(object):
    def setupUi(self, PropertyWidget):
        PropertyWidget.setObjectName("PropertyWidget")
        PropertyWidget.resize(600, 24)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(PropertyWidget.sizePolicy().hasHeightForWidth())
        PropertyWidget.setSizePolicy(sizePolicy)
        PropertyWidget.setMinimumSize(QtCore.QSize(0, 24))
        PropertyWidget.setMaximumSize(QtCore.QSize(16777215, 24))
        PropertyWidget.setFocusPolicy(QtCore.Qt.NoFocus)
        PropertyWidget.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.horizontalLayout = QtGui.QHBoxLayout(PropertyWidget)
        self.horizontalLayout.setSpacing(5)
        self.horizontalLayout.setContentsMargins(1, 1, 1, 1)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.nameLabel = QtGui.QLabel(PropertyWidget)
        self.nameLabel.setEnabled(False)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.nameLabel.sizePolicy().hasHeightForWidth())
        self.nameLabel.setSizePolicy(sizePolicy)
        self.nameLabel.setMinimumSize(QtCore.QSize(75, 0))
        self.nameLabel.setMaximumSize(QtCore.QSize(75, 30))
        self.nameLabel.setBaseSize(QtCore.QSize(0, 0))
        self.nameLabel.setFrameShape(QtGui.QFrame.NoFrame)
        self.nameLabel.setText("")
        self.nameLabel.setTextFormat(QtCore.Qt.AutoText)
        self.nameLabel.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.nameLabel.setWordWrap(True)
        self.nameLabel.setMargin(1)
        self.nameLabel.setObjectName("nameLabel")
        self.horizontalLayout.addWidget(self.nameLabel)
        self.dataLabel = QtGui.QLabel(PropertyWidget)
        self.dataLabel.setFrameShape(QtGui.QFrame.StyledPanel)
        self.dataLabel.setFrameShadow(QtGui.QFrame.Plain)
        self.dataLabel.setText("")
        self.dataLabel.setTextInteractionFlags(QtCore.Qt.TextSelectableByKeyboard)
        self.dataLabel.setObjectName("dataLabel")
        self.horizontalLayout.addWidget(self.dataLabel)

        self.retranslateUi(PropertyWidget)
        QtCore.QMetaObject.connectSlotsByName(PropertyWidget)

    def retranslateUi(self, PropertyWidget):
        PropertyWidget.setWindowTitle(QtGui.QApplication.translate("PropertyWidget", "Form", None, QtGui.QApplication.UnicodeUTF8))

