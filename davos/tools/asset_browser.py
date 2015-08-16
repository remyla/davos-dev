
import sys

from PySide import QtGui

from davos.gui.assetbrowserwindow import AssetBrowserWindow
from pytd.util.sysutils import inDevMode

WINDOW_NAME = "assetBrowserWin"

def launch(sProject, argv):

    app = QtGui.QApplication(argv)

    #print QtGui.QStyleFactory.keys()
    app.setStyle("Cleanlooks")

    mainWin = AssetBrowserWindow(WINDOW_NAME)
    mainWin.show()

    if 1:
        mainWin.setProject(sProject)

    sys.exit(app.exec_())


if __name__ == "__main__":

    launch("zombtest" if inDevMode() else "zombillenium", sys.argv)
