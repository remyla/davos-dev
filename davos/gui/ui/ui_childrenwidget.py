# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\styx\DEVSPACE\git\z2k-pipeline-toolkit\python\davos-dev\resources\ui\childrenwidget.ui'
#
# Created: Thu Aug 20 09:19:51 2015
#      by: pyside-uic 0.2.14 running on PySide 1.2.0
#
# WARNING! All changes made in this file will be lost!

from PySide import QtCore, QtGui

class Ui_ChildrenWidget(object):
    def setupUi(self, ChildrenWidget):
        ChildrenWidget.setObjectName("ChildrenWidget")
        ChildrenWidget.resize(696, 546)
        self.verticalLayout = QtGui.QVBoxLayout(ChildrenWidget)
        self.verticalLayout.setSpacing(2)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.pathToolBar = ToolBar(ChildrenWidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pathToolBar.sizePolicy().hasHeightForWidth())
        self.pathToolBar.setSizePolicy(sizePolicy)
        self.pathToolBar.setMinimumSize(QtCore.QSize(50, 25))
        self.pathToolBar.setObjectName("pathToolBar")
        self.verticalLayout.addWidget(self.pathToolBar)
        self.childrenView = ChildrenView(ChildrenWidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.childrenView.sizePolicy().hasHeightForWidth())
        self.childrenView.setSizePolicy(sizePolicy)
        self.childrenView.setObjectName("childrenView")
        self.verticalLayout.addWidget(self.childrenView)
        self.splitter = QtGui.QSplitter(ChildrenWidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.splitter.sizePolicy().hasHeightForWidth())
        self.splitter.setSizePolicy(sizePolicy)
        self.splitter.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.splitter.setFrameShape(QtGui.QFrame.NoFrame)
        self.splitter.setFrameShadow(QtGui.QFrame.Plain)
        self.splitter.setOrientation(QtCore.Qt.Horizontal)
        self.splitter.setHandleWidth(4)
        self.splitter.setChildrenCollapsible(True)
        self.splitter.setObjectName("splitter")
        self.layoutWidget = QtGui.QWidget(self.splitter)
        self.layoutWidget.setObjectName("layoutWidget")
        self.filterLayout = QtGui.QHBoxLayout(self.layoutWidget)
        self.filterLayout.setSpacing(1)
        self.filterLayout.setContentsMargins(3, 1, 1, 1)
        self.filterLayout.setObjectName("filterLayout")
        self.filterLabel = QtGui.QLabel(self.layoutWidget)
        self.filterLabel.setObjectName("filterLabel")
        self.filterLayout.addWidget(self.filterLabel)
        self.filterEdit = QtGui.QLineEdit(self.layoutWidget)
        self.filterEdit.setMaximumSize(QtCore.QSize(16777215, 20))
        self.filterEdit.setObjectName("filterEdit")
        self.filterLayout.addWidget(self.filterEdit)
        self.layoutWidget1 = QtGui.QWidget(self.splitter)
        self.layoutWidget1.setObjectName("layoutWidget1")
        self.zoomLayout = QtGui.QHBoxLayout(self.layoutWidget1)
        self.zoomLayout.setSpacing(1)
        self.zoomLayout.setContentsMargins(1, 1, 1, 1)
        self.zoomLayout.setContentsMargins(0, 0, 0, 0)
        self.zoomLayout.setObjectName("zoomLayout")
        self.zoomOutLabel = QtGui.QLabel(self.layoutWidget1)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.zoomOutLabel.sizePolicy().hasHeightForWidth())
        self.zoomOutLabel.setSizePolicy(sizePolicy)
        self.zoomOutLabel.setMaximumSize(QtCore.QSize(20, 20))
        self.zoomOutLabel.setText("")
        self.zoomOutLabel.setPixmap(QtGui.QPixmap(":/icons/icons/zoomOut.png"))
        self.zoomOutLabel.setScaledContents(True)
        self.zoomOutLabel.setObjectName("zoomOutLabel")
        self.zoomLayout.addWidget(self.zoomOutLabel)
        self.rowHeightSlider = QtGui.QSlider(self.layoutWidget1)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.rowHeightSlider.sizePolicy().hasHeightForWidth())
        self.rowHeightSlider.setSizePolicy(sizePolicy)
        self.rowHeightSlider.setMaximumSize(QtCore.QSize(16777215, 20))
        self.rowHeightSlider.setOrientation(QtCore.Qt.Horizontal)
        self.rowHeightSlider.setObjectName("rowHeightSlider")
        self.zoomLayout.addWidget(self.rowHeightSlider)
        self.zoomInLabel = QtGui.QLabel(self.layoutWidget1)
        self.zoomInLabel.setMaximumSize(QtCore.QSize(20, 20))
        self.zoomInLabel.setFrameShape(QtGui.QFrame.NoFrame)
        self.zoomInLabel.setText("")
        self.zoomInLabel.setPixmap(QtGui.QPixmap(":/icons/icons/zoomIn.png"))
        self.zoomInLabel.setScaledContents(False)
        self.zoomInLabel.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.zoomInLabel.setMargin(-3)
        self.zoomInLabel.setIndent(-1)
        self.zoomInLabel.setObjectName("zoomInLabel")
        self.zoomLayout.addWidget(self.zoomInLabel)
        self.verticalLayout.addWidget(self.splitter)

        self.retranslateUi(ChildrenWidget)
        QtCore.QMetaObject.connectSlotsByName(ChildrenWidget)

    def retranslateUi(self, ChildrenWidget):
        ChildrenWidget.setWindowTitle(QtGui.QApplication.translate("ChildrenWidget", "Form", None, QtGui.QApplication.UnicodeUTF8))
        self.filterLabel.setText(QtGui.QApplication.translate("ChildrenWidget", "Filter :", None, QtGui.QApplication.UnicodeUTF8))

from davos.gui.childrenview import ChildrenView
from pytd.gui.widgets import ToolBar