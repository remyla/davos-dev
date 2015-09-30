
import os

#from PySide.QtCore import Slot, QObject
from PySide import QtGui

from pytd.util.sysutils import inDevMode, toStr, hostApp

from .ui.ui_assetbrowserwindow import Ui_AssetBrowserWin
from .assetbrowserwidget import AssetBrowserWidget
from pytd.gui.dialogs import confirmDialog

STYLE = """
QMainWindow{
    border-style: dashed;
    border-width: 1px;
    border-color: red;
}
 """

class AssetBrowserWindow(QtGui.QMainWindow, Ui_AssetBrowserWin):

    classBrowserWidget = AssetBrowserWidget

    def __init__(self, windowName="", windowTitle="", parent=None):
        super(AssetBrowserWindow, self).__init__(parent)

        self.setupUi(self)
        if windowName:
            self.setObjectName(windowName)
        if windowTitle:
            self.setWindowTitle(windowTitle)

        self.browserWidget = self.__class__.classBrowserWidget(self)
        self.setCentralWidget(self.browserWidget)

        self.resize(1100, 800)

        if inDevMode():
            self.setStyleSheet(STYLE)

    def setProject(self, *args, **kwargs):

        try:
            return self.browserWidget.setProject(*args, **kwargs)
        except Exception, err:
            confirmDialog(title='SORRY !'
                        , message=toStr(err)
                        , button=["OK"]
                        , defaultButton="OK"
                        , cancelButton="OK"
                        , dismissString="OK"
                        , icon="critical")

            if not hostApp():
                os.environ["PYTHONINSPECT"] = "1"

            self.close()

            raise

#    def __del__(self):
#        print "__del__", self.objectName()

#    def closeEvent(self, event):
#        print self, "closeEvent"
#        return QtGui.QMainWindow.closeEvent(self, event)