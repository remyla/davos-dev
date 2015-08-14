# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\sebcourtois\devspace\git\z2k-pipeline-toolkit\python\davos-dev\resources\ui\asset_browser_window.ui'
#
# Created: Fri Aug 14 18:52:52 2015
#      by: pyside-uic 0.2.14 running on PySide 1.2.0
#
# WARNING! All changes made in this file will be lost!

from PySide import QtCore, QtGui

class Ui_AssetBrowserWin(object):
    def setupUi(self, AssetBrowserWin):
        AssetBrowserWin.setObjectName("AssetBrowserWin")
        AssetBrowserWin.resize(1100, 789)
        self.centralWidget = QtGui.QWidget(AssetBrowserWin)
        self.centralWidget.setObjectName("centralWidget")
        AssetBrowserWin.setCentralWidget(self.centralWidget)
        self.menuBar = QtGui.QMenuBar(AssetBrowserWin)
        self.menuBar.setGeometry(QtCore.QRect(0, 0, 1100, 21))
        self.menuBar.setNativeMenuBar(True)
        self.menuBar.setObjectName("menuBar")
        AssetBrowserWin.setMenuBar(self.menuBar)
        self.statusBar = QtGui.QStatusBar(AssetBrowserWin)
        self.statusBar.setEnabled(True)
        self.statusBar.setSizeGripEnabled(True)
        self.statusBar.setObjectName("statusBar")
        AssetBrowserWin.setStatusBar(self.statusBar)
        self.toolBar = QtGui.QToolBar(AssetBrowserWin)
        self.toolBar.setMovable(False)
        self.toolBar.setFloatable(False)
        self.toolBar.setObjectName("toolBar")
        AssetBrowserWin.addToolBar(QtCore.Qt.TopToolBarArea, self.toolBar)

        self.retranslateUi(AssetBrowserWin)
        QtCore.QMetaObject.connectSlotsByName(AssetBrowserWin)

    def retranslateUi(self, AssetBrowserWin):
        AssetBrowserWin.setWindowTitle(QtGui.QApplication.translate("AssetBrowserWin", "Asset Browser", None, QtGui.QApplication.UnicodeUTF8))
        self.toolBar.setWindowTitle(QtGui.QApplication.translate("AssetBrowserWin", "toolBar", None, QtGui.QApplication.UnicodeUTF8))

