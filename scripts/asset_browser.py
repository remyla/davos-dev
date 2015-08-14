
import os
import sys

from PySide import QtGui

sys.path.append(r'C:\Users\sebcourtois\devspace\git\z2k-pipeline-toolkit\launchers\paris')
import setup_env_tools
setup_env_tools.loadEnviron()

os.environ["DEV_MODE_ENV"] = ""

from davos.gui.assetbrowserwindow import AssetBrowserWindow

WINDOW_NAME = "assetBrowserWin"

def launch(argv):

    app = QtGui.QApplication(argv)

    #print QtGui.QStyleFactory.keys()
    app.setStyle("Cleanlooks")

    mainWin = AssetBrowserWindow(WINDOW_NAME)
    mainWin.show()

    mainWin.setProject("zombtest")

    sys.exit(app.exec_())

if __name__ == "__main__":
    launch(sys.argv)
