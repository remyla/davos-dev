
import os
import sys

from PySide import QtGui
from PySide.QtGui import QTreeWidgetItem, QTreeWidgetItemIterator
from PySide.QtCore import Qt

from davos.core.damproject import DamProject
from pytd.util.sysutils import qtGuiApp
from pytd.gui.dialogs import confirmDialog, SimpleTreeDialog

class TreeItem(QTreeWidgetItem):

    def __init__(self, *args, **kwargs):
        super(TreeItem, self).__init__(*args, **kwargs)
        #self.setFlags(self.flags() | Qt.ItemIsTristate)

def launch(dryRun=True, project=""):

    app = qtGuiApp()
    if not app:
        app = QtGui.QApplication(sys.argv)

    sProject = os.environ["DAVOS_INIT_PROJECT"] if not project else project
    proj = DamProject(sProject)
    print sProject.center(80, "-")

    dbNodeDct = {}

    sFieldSet = set()
    for n in proj.findDbNodes():
        sFieldSet.update(n._data.iterkeys())
        dbNodeDct.setdefault(n.file.lower(), []).append(n)

    dlg = SimpleTreeDialog()
    treeWdg = dlg.treeWidget

    sFieldList = sorted(sFieldSet)
    sFieldList.remove("file")
    sFieldList.remove("#parent")
    sFieldList.insert(0, "file")

    treeWdg.setHeaderLabels(sFieldList)
    treeWdg.setTextElideMode(Qt.ElideLeft)

    topLevelItemDct = {}
    for sDbPath, nodes in dbNodeDct.iteritems():
        x = len(nodes)
        if x > 1:
            nodes = sorted(nodes, key=lambda x:int(x.time) * .001, reverse=True)

            if sDbPath not in topLevelItemDct:
                topItem = TreeItem(treeWdg, [sDbPath])
                topLevelItemDct[sDbPath] = topItem
            else:
                topItem = topLevelItemDct[sDbPath]

            for n in nodes:

                data = tuple(n._data.get(f, "") for f in sFieldList)
                item = TreeItem(topItem, data)
                item.setCheckState(0, Qt.Unchecked)
                item.setData(0, Qt.UserRole, n)

    treeWdg.expandAll()
    for c in xrange(treeWdg.columnCount()):
        treeWdg.resizeColumnToContents(c)

    bOk = dlg.exec_()
    if not bOk:
        return

    itemIter = QTreeWidgetItemIterator(treeWdg, QTreeWidgetItemIterator.Checked)
    toDeleteNodes = [item.value().data(0, Qt.UserRole) for item in itemIter]
    if toDeleteNodes:
        sMsg = "Delete these {} Db nodes ???".format(len(toDeleteNodes))
        sConfirm = confirmDialog(title="WARNING !",
                                 message=sMsg,
                                 button=("Yes", "No"),
                                 defaultButton="No",
                                 cancelButton="No",
                                 dismissString="No",
                                 icon="warning",
                                )

        if sConfirm == "Yes":
            for n in toDeleteNodes:
                print "Deleting", n.file, n._data
                if not dryRun:
                    n.delete()

