
import sys

from PySide import QtGui

from davos.gui.assetbrowserwindow import AssetBrowserWindow

WINDOW_NAME = "assetBrowserWin"

def launch(argv):

    app = QtGui.QApplication(argv)

    #print QtGui.QStyleFactory.keys()
    app.setStyle("Cleanlooks")

    mainWin = AssetBrowserWindow(WINDOW_NAME)
    mainWin.show()

    if 1:
        mainWin.setProject("zombtest")

    sys.exit(app.exec_())

if __name__ == "__main__":
    launch(sys.argv)
