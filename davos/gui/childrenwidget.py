

from PySide import QtGui, QtCore
from PySide.QtCore import Qt

from pytd.util.sysutils import toUnicode

from pytd.gui.itemviews.baseproxymodel import BaseProxyModel
from pytd.gui.itemviews.baseselectionmodel import BaseSelectionModel

from .ui.children_widget import Ui_ChildrenWidget

class ChildrenProxyModel(BaseProxyModel):

    def __init__(self, parent=None):
        super(ChildrenProxyModel, self).__init__(parent)

        #self.imageSection = -1

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
        slider.setMinimum(16)
        slider.setMaximum(64)

        slider.valueChanged.connect(self.childrenView.setItemHeight)
        slider.setValue(self.childrenView.itemHeight)

        self.pathToolBar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.pathToolBar.setIconSize(QtCore.QSize(16, 16))
        self.pathToolBar.actionTriggered.connect(self.pathActionTriggered)

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

    def pathActionTriggered(self, action):

        pathToolBar = self.pathToolBar

        newRootItem = pathToolBar.actionData(action)
        if newRootItem:

            childItem = None
            actionList = pathToolBar.actions()
            if actionList:
                childItem = pathToolBar.actionData(actionList[-1])

            self.changeRootIndex(self.model().indexFromItem(newRootItem))

            if childItem:
                self.revealItem(childItem)

    def updatePathBar(self, index):

        pathToolBar = self.pathToolBar
        childrenView = self.childrenView

        pathToolBar.actionTriggered.disconnect(self.pathActionTriggered)

        def restore():
            pathToolBar.actionTriggered.connect(self.pathActionTriggered)

        pathToolBar.clear()

        if index.column() != 0:
            parentIndex = index.sibling(index.row(), 0)
        else:
            parentIndex = index

        bBreak = False

        treeRoot = childrenView.model().invisibleRootItem()

        count = 0
        prevAction = None
        while True:

            if not parentIndex.isValid():
                parentItem = treeRoot
                sLabel = "Root"
                bBreak = True
            else:
                model = parentIndex.model()
                parentItem = model.itemFromIndex(parentIndex)
                sLabel = toUnicode(model.data(parentIndex, Qt.DisplayRole))

            sLabel += " /"

            viewIndex = childrenView.mappedIdx(parentIndex)
            icon = viewIndex.data(Qt.DecorationRole)
            if not icon:
                icon = QtGui.QIcon()

            if count == 0:
                curAction = pathToolBar.addAction(icon, sLabel)
            else:
                curAction = pathToolBar.addAction(icon, sLabel)
                pathToolBar.insertAction(prevAction, curAction)

            pathToolBar.setActionData(curAction, parentItem)

            if bBreak:
                break

            prevAction = curAction
            parentIndex = parentIndex.parent()

            count += 1

        restore()
