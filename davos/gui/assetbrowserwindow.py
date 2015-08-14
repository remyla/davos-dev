
from PySide import QtGui

from pytd.util.strutils import labelify

from .ui.asset_browser_window import Ui_AssetBrowserWin
from .assetbrowserwidget import AssetBrowserWidget

class AssetBrowserWindow(QtGui.QMainWindow, Ui_AssetBrowserWin):

    classBrowserWidget = AssetBrowserWidget

    def __init__(self, sWindowName, windowTitle="", parent=None):
        super(AssetBrowserWindow, self).__init__(parent)

        self.setupUi(self)
        self.setObjectName(sWindowName)
        self.setWindowTitle(windowTitle if windowTitle else labelify(sWindowName))

        self.browserWidget = self.__class__.classBrowserWidget(self)
        self.setCentralWidget(self.browserWidget)

        self.resize(1100, 800)

    def setProject(self, *args, **kwargs):
        self.browserWidget.setProject(*args, **kwargs)