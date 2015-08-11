
from PySide import QtGui

from .ui.asset_browser_window import Ui_AssetBrowserWin

WINDOW_NAME = "assetBrowserWin"

class AssetBrowserWindow(QtGui.QMainWindow, Ui_AssetBrowserWin):

    def __init__(self, parent=None):
        super(AssetBrowserWindow , self).__init__(parent)

        self.setupUi(self)
        self.setObjectName(WINDOW_NAME)
