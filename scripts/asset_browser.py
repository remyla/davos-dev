
import sys

from PySide import QtGui

import os

sys.path.append(r'C:\Users\sebcourtois\devspace\git\z2k-pipeline-toolkit\launchers\paris')
import setup_env_tools
setup_env_tools.loadEnviron()

os.environ["DEV_MODE_ENV"] = ""

from davos.core.damproject import DamProject
from davos.gui.assetbrowserwidget import AssetBrowserWidget

def main(argv):

    app = QtGui.QApplication(argv)

    # print QtGui.QStyleFactory.keys()
    app.setStyle("Cleanlooks")

    mainWin = QtGui.QMainWindow()
    view = AssetBrowserWidget(mainWin)
    mainWin.setCentralWidget(view)
    mainWin.resize(1100, 800)
    mainWin.show()

    proj = DamProject("zombdev", empty=True)
    if proj:
        proj.init()
        view.setupModelData(proj)
        proj.loadLibraries(noError=True)

    sys.exit(app.exec_())


if __name__ == "__main__":
    main(sys.argv)
