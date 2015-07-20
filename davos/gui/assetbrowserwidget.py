
from PySide import QtCore
from PySide import QtGui
Qt = QtCore.Qt

from .ui.asset_browser_widget import Ui_AssetBrowserWidget

class AssetBrowserWidget(QtGui.QWidget, Ui_AssetBrowserWidget):

    def __init__(self, parent=None):
        super(AssetBrowserWidget , self).__init__(parent)

        self.setupUi(self)
        self.splitter.splitterMoved.connect(self.autoResizeImage)

    def autoResizeImage(self, *args):
        self.propertyEditorView.resizeImageButton(self.splitter.sizes()[1])

    def setupModelData(self, metamodel):

        treeWidget = self.treeWidget

        self.propertyEditorView.disconnectFromTreeWidget()

        treeWidget.setupModelData(metamodel)

        self.propertyEditorView.connectToTreeWidget(treeWidget)


