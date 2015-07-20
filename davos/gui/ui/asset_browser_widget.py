# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\sebcourtois\devspace\cg-pypeline-toolkit\resources\davos\asset_browser_widget.ui'
#
# Created: Wed Jun 24 18:47:32 2015
#      by: pyside-uic 0.2.14 running on PySide 1.2.0
#
# WARNING! All changes made in this file will be lost!

from PySide import QtCore, QtGui

class Ui_AssetBrowserWidget(object):
    def setupUi(self, AssetBrowserWidget):
        AssetBrowserWidget.setObjectName("AssetBrowserWidget")
        AssetBrowserWidget.resize(1000, 800)
        self.verticalLayout = QtGui.QVBoxLayout(AssetBrowserWidget)
        self.verticalLayout.setObjectName("verticalLayout")
        self.splitter = QtGui.QSplitter(AssetBrowserWidget)
        self.splitter.setOrientation(QtCore.Qt.Vertical)
        self.splitter.setHandleWidth(4)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setObjectName("splitter")
        self.treeWidget = BrowserTreeWidget(self.splitter)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.treeWidget.sizePolicy().hasHeightForWidth())
        self.treeWidget.setSizePolicy(sizePolicy)
        self.treeWidget.setObjectName("treeWidget")
        self.propertyEditorView = PropertyEditorView(self.splitter)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Ignored)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.propertyEditorView.sizePolicy().hasHeightForWidth())
        self.propertyEditorView.setSizePolicy(sizePolicy)
        self.propertyEditorView.setStyleSheet("")
        self.propertyEditorView.setObjectName("propertyEditorView")
        self.verticalLayout.addWidget(self.splitter)

        self.retranslateUi(AssetBrowserWidget)
        QtCore.QMetaObject.connectSlotsByName(AssetBrowserWidget)

    def retranslateUi(self, AssetBrowserWidget):
        AssetBrowserWidget.setWindowTitle(QtGui.QApplication.translate("AssetBrowserWidget", "Form", None, QtGui.QApplication.UnicodeUTF8))

from pytk.davos.gui.propertyeditorview import PropertyEditorView
from pytk.davos.gui.browsertreewidget import BrowserTreeWidget
