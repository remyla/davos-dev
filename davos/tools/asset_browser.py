
import sys
import os

from PySide import QtGui

from davos.gui.assetbrowserwindow import AssetBrowserWindow

WINDOW_NAME = "assetBrowserWin"

def launch(sProject, argv):

    app = QtGui.QApplication(argv)

    #print QtGui.QStyleFactory.keys()
    app.setStyle("Cleanlooks")

    mainWin = AssetBrowserWindow(WINDOW_NAME)
    mainWin.show()

    if sProject:
        mainWin.setProject(sProject)

    sys.exit(app.exec_())


if __name__ == "__main__":

    launch(os.environ.get("DAVOS_INIT_PROJECT"), sys.argv)
