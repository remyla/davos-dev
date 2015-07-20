
from PySide import QtGui
from PySide import QtCore
from PySide.QtCore import Qt

#from pytk.core.itemviews.basecontextmenu import BaseContextMenu
from pytk.core.itemviews.basetreeview import BaseTreeView

from .browsercontextmenu import BrowserContextMenu

class ChildrenView(BaseTreeView):

    contextMenuClass = BrowserContextMenu

    rootIndexChanged = QtCore.Signal(QtCore.QModelIndex)

    def __init__(self, parent=None):
        super(ChildrenView, self).__init__(parent)

        self.setObjectName("childrenView")

        self.mainCtxMenu = None
        self.contextMenuEnabled = True

        self.setItemDelegate(QtGui.QStyledItemDelegate(self))
        self.setMouseTracking(True)

        self.setItemsExpandable(False)
        self.setExpandsOnDoubleClick(False)
        self.setRootIsDecorated(False)

        self.setAllColumnsShowFocus(True)
        self.setAlternatingRowColors(True)

        self.setSortingEnabled(True)

        #self.setStyleSheet(uiModelView.viewStyleSheet)
        self.doubleClicked.connect(self.changeRootIndex)
#        self.clicked.connect( self.test )

    def test(self, index):

        if not index.isValid():
            return

        print self.selectionModel().selectedLeaves

#        model = index.model()
#        if model:
#            leaf = model.leafForIndex( index )
#            if leaf:
#                if leaf.index:
#                    print leaf, "src index:", leaf.index.row()
#                if leaf.prxIndex:
#                    print leaf, "prx index:", leaf.prxIndex.row()

    def changeRootIndex(self, in_index):

        if in_index.column() != 0:
            index = in_index.sibling(in_index.row(), 0)
        else:
            index = in_index

        newRootIndex = self.mappedIdx(index)

        if not newRootIndex.isValid():
            self.reset()
            self.updateGeometries()
        elif (newRootIndex == self.rootIndex()):
            return

        viewModel = self.model()
        newRootItem = viewModel.itemFromIndex(newRootIndex)
        if newRootItem:

            if not newRootItem.hasChildren():
                return

            if isinstance(viewModel, QtGui.QSortFilterProxyModel):
                viewModel.filterRootIndex = viewModel.sourceModel().indexFromItem(newRootItem)

#            sPropertyList = newRootItem.__class__.childrenViewProperties
#            for i, sProperty in enumerate(viewModel.propertyList):
#                self.setColumnHidden(i, (sProperty not in sPropertyList))

        self.setRootIndex(newRootIndex)
        self.selectionModel().clear()
        self.resizeColumnsToContents()
        self.rootIndexChanged.emit(newRootIndex)

    def backToParentIndex(self):

        curntRootIdx = self.rootIndex()
        self.changeRootIndex(curntRootIdx.parent())
        self.selectIndex(curntRootIdx)

    def setModel(self, model):
        BaseTreeView.setModel(self, model)

        if self.contextMenuEnabled:
            self.mainCtxMenu = self.__class__.contextMenuClass(self)

        self.sortByColumn(0, Qt.AscendingOrder)

        headerView = self.header()
        if headerView.visualIndex(model.imageSection) > 0:
            headerView.moveSection(model.imageSection, 0)
        headerView.setResizeMode(model.imageSection, QtGui.QHeaderView.Fixed)

#        # hiding unwanted column
#        sPropertyList = Item.childrenViewProperties
#        for i, sProperty in enumerate(model.propertyList):
#                self.setColumnHidden(i, sProperty not in sPropertyList)

        self.resizeColumnsToContents()

    def contextMenuEvent(self, event):
        ctxMenu = self.mainCtxMenu
        if ctxMenu:
            ctxMenu.launch(event)

    def selectLeaf(self, *leafList , **kwargs):

        model = self.model()

        indexes = tuple(model.indexForLeaf(leaf) for leaf in leafList if (leaf.isInTree() and (leaf != model.root)))

        self.selectIndex(*indexes, **kwargs)

    def revealItem(self, item, **kwargs):

        bAsRoot = kwargs.get("asRoot", False)

        index = self.model().indexFromItem(item)
        if index.isValid():

            if bAsRoot:
                self.changeRootIndex(index)

#            print "valid", leaf, getCaller( fo = False, depth = 5 )
            self.selectIndex(index)

#        else:
#            print "invalid", leaf, getCaller( fo = False, depth = 5 )

        return

    def getSectionId(self, sProperty):

        model = self.model()

        try:
            idx = model.propertyNames.index(sProperty)
        except ValueError:
            idx = -1

        return idx
