

from PySide import QtGui
from PySide.QtCore import Qt

from pytk.util.sysutils import toUnicode

from pytk.core.itemviews.baseproxymodel import BaseProxyModel
from pytk.core.itemviews.baseselectionmodel import BaseSelectionModel

from .ui.children_widget import Ui_ChildrenWidget

class ChildrenProxyModel(BaseProxyModel):

    def __init__(self, parent=None):
        super(ChildrenProxyModel, self).__init__(parent)

        self.imageSection = -1

        self.setDynamicSortFilter(True)
        self.setFilterCaseSensitivity(Qt.CaseInsensitive)

#    def data(self, index, role):
#
#        column = index.column()
#
#        if column == self.imageSection:
#
#            if role == Qt.DecorationRole:
#
#                leaf = self.leafForIndex(index)
#                if leaf and leaf.thumbnail:
#                    return leaf.thumbnail
#                else:
#                    return QtGui.QPixmap()
#
#            else:
#                return
#
#        elif role == Qt.DecorationRole:
#            return QtGui.QPixmap()
#
#        else:
#            return QtGui.QSortFilterProxyModel.data(self, index, role)

    def setSourceModel(self, model):
        BaseProxyModel.setSourceModel(self, model)
        self.filterRootIndex = model.indexFromItem(self.sourceModel().invisibleRootItem())

    def filterAcceptsRow(self, srcRow, srcParentIndex):

        regExp = self.filterRegExp()

        if not regExp.isValid():
            return True

        if regExp.isEmpty():
            return True

        if srcParentIndex == self.filterRootIndex:

            srcModel = self.sourceModel()
            srcIndex = srcModel.index(srcRow, 0, srcParentIndex)

            if srcIndex.parent() != self.filterRootIndex:
                return True

            bMatch = (regExp.indexIn(srcIndex.data(self.filterRole())) != -1)

            return bMatch

        return True


class ChildrenWidget(QtGui.QWidget, Ui_ChildrenWidget):

    selectModelClass = BaseSelectionModel

    def __init__(self, parent=None):
        super(ChildrenWidget, self).__init__(parent)

        self.setupUi(self)

        slider = self.rowHeightSlider
        slider.setMinimum(32)
        slider.setMaximum(128)

        #slider.valueChanged.connect(self.childrenView.setItemHeight)
        #slider.setValue(self.childrenView.itemHeight)

        self.pathTabBar.currentChanged.connect(self.tabChanged)

    def setModel(self, treeModel):

        if isinstance(treeModel, QtGui.QSortFilterProxyModel):
            srcModel = treeModel.sourceModel()
            model = ChildrenProxyModel()
            model.setSourceModel(srcModel)
        else:
            model = treeModel

        self.childrenView.setModel(model)
        if isinstance(model, QtGui.QSortFilterProxyModel):
            self.filterEdit.textChanged.connect(model.setFilterWildcard)

        self.setSelectionModel(self.__class__.selectModelClass(model))

    def setSelectionModel(self, selectionModel):
        self.childrenView.setSelectionModel(selectionModel)

    def selectionModel(self):
        return self.childrenView.selectionModel()

    def model(self):
        return self.childrenView.model()

    def changeRootIndex(self, viewIndex):

        self.filterEdit.clear()
        self.childrenView.changeRootIndex(viewIndex)

    def revealItem(self, item, **kwargs):
        self.childrenView.revealItem(item, **kwargs)

    def setContextMenuEnabled(self, bEnable):
        self.childrenView.contextMenuEnabled = bEnable

    def getSelectedLeaves(self):
        return self.childrenView.selectionModel().selectedLeaves[:]

    def backToParentIndex(self):
        if self.isVisible():
            self.childrenView.backToParentIndex()

    def tabChanged(self, tabIdx):

        pathTabBar = self.pathTabBar

        newRootItem = pathTabBar.tabData(tabIdx)
        if newRootItem:

            childItem = pathTabBar.tabData(tabIdx + 1)

            self.changeRootIndex(self.model().indexFromItem(newRootItem))

            if childItem:
                self.revealItem(childItem)

    def updatePathBar(self, in_index):

        pathTabBar = self.pathTabBar
        childrenView = self.childrenView

        pathTabBar.currentChanged.disconnect(self.tabChanged)

        def restore():
            pathTabBar.currentChanged.connect(self.tabChanged)

        pathTabBar.clear()

        if in_index.column() != 0:
            parentIndex = in_index.sibling(in_index.row(), 0)
        else:
            parentIndex = in_index

        bBreak = False

        treeRoot = childrenView.model().invisibleRootItem()

        count = 0
        while True:

            if not parentIndex.isValid():
                parentItem = treeRoot
                sLabel = "Root"
                bBreak = True
            else:
                model = parentIndex.model()
                parentItem = model.itemFromIndex(parentIndex)
                sLabel = toUnicode(model.data(parentIndex, Qt.DisplayRole))

            if count == 0:
                iNewTab = pathTabBar.addTab(sLabel)
            else:
                iNewTab = pathTabBar.insertTab(0, sLabel)

            pathTabBar.setTabData(iNewTab, parentItem)

            viewIndex = childrenView.mappedIdx(parentIndex)
            icon = viewIndex.data(Qt.DecorationRole)
            if icon:
                pathTabBar.setTabIcon(iNewTab, QtGui.QIcon(icon))

            if bBreak:
                break

            parentIndex = parentIndex.parent()

            count += 1

        restore()
