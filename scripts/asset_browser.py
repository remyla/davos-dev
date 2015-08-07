
import os
import sys

os.environ["DEV_MODE_ENV"] = '1'

from PySide import QtGui

from davos.core.damproject import DamProject

from davos.gui.assetbrowserwidget import AssetBrowserWidget


def main(argv):

    app = QtGui.QApplication(argv)

    # print QtGui.QStyleFactory.keys()
    app.setStyle("Cleanlooks")

    mainWin = QtGui.QMainWindow()
    view = AssetBrowserWidget(mainWin)
    mainWin.setCentralWidget(view)
    mainWin.resize(1200, 800)
    mainWin.show()

    proj = DamProject("zombillenium", empty=True)
    if proj:
        proj.init()
        view.setupModelData(proj)
        proj.loadLibraries()

    sys.exit(app.exec_())


if __name__ == "__main__":

    main(sys.argv)
