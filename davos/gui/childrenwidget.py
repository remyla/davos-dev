

from PySide import QtGui
from PySide.QtCore import Qt
from PySide.QtCore import QSize

from pytd.util.sysutils import toUnicode

from pytd.gui.itemviews.baseproxymodel import BaseProxyModel
from pytd.gui.itemviews.baseselectionmodel import BaseSelectionModel

from .ui.children_widget import Ui_ChildrenWidget


_PATH_BAR_SS = """
QToolBar{
    spacing:0px;
}

QToolButton{
    padding-right:  -1px;
    padding-left:   -1px;
    padding-top:     1px;
    padding-bottom:  1px;
}
"""

class ChildrenProxyModel(BaseProxyModel):

    def __init__(self, parent=None):
        super(ChildrenProxyModel, self).__init__(parent)

        self.setDynamicSortFilter(True)
        self.setFilterCaseSensitivity(Qt.CaseInsensitive)

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

        self.pathToolBar.setStyleSheet(_PATH_BAR_SS)
        self.pathToolBar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.pathToolBar.setIconSize(QSize(16, 16))
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

            if icon.isNull():
                toolBtn = pathToolBar.widgetForAction(curAction)
                toolBtn.setArrowType(Qt.RightArrow)

            if bBreak:
                break

            prevAction = curAction
            parentIndex = parentIndex.parent()

            count += 1

        restore()
