
import os
import sys

os.environ["DEV_MODE_ENV"] = ''

from PySide import QtGui

from davos.core.damproject import DamProject

from davos.gui.assetbrowserwidget import AssetBrowserWidget


def main(argv):

    app = QtGui.QApplication(argv)

    # print QtGui.QStyleFactory.keys()
    app.setStyle("Cleanlooks")

    view = AssetBrowserWidget()
    view.show()

    proj = DamProject("zombillenium", empty=True)
    if proj:
        proj.init()
        view.setupModelData(proj)
        proj.loadLibraries()

    sys.exit(app.exec_())


if __name__ == "__main__":

    main(sys.argv)
