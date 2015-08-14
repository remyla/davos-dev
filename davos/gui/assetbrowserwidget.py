
from PySide import QtCore
from PySide import QtGui
Qt = QtCore.Qt

from pytd.util.sysutils import timer
from pytd.util.strutils import labelify
from pytd.util.sysutils import inDevMode

from davos.core.damproject import DamProject

from .ui.asset_browser_widget import Ui_AssetBrowserWidget

STYLE = """
QTreeView{
    border-style: dashed;
    border-width: 1px;
    border-color: red;
}
 """

class AssetBrowserWidget(QtGui.QWidget, Ui_AssetBrowserWidget):

    def __init__(self, parent=None):
        super(AssetBrowserWidget , self).__init__(parent)

        self.setupUi(self)
        self.splitter.splitterMoved.connect(self.autoResizeImage)

        self.project = None

        if inDevMode():
            self.setStyleSheet(STYLE)

    def autoResizeImage(self, *args):
        self.propertyEditorView.resizeImageButton(self.splitter.sizes()[1])

    def setProject(self, newProj, curntProj=None, **kwargs):

        bStandalone = kwargs.pop("standalone", False)

        if bStandalone:
            curntProj = None

        if isinstance(newProj, DamProject):
            proj = newProj
        else:
            if isinstance(newProj, basestring):
                sNewProjName = newProj
            else:
                raise TypeError, "Cannot set new project from {0}.".format(type(newProj))

            if curntProj and (sNewProjName == curntProj.name):
                proj = curntProj
            else:
                proj = DamProject(sNewProjName, empty=True, **kwargs)

        if proj:
#            if self.projSelector.currentText() != proj.name:
#                self.projSelector.selectProject(proj.name)
            self.loadProject(proj)

        else:#loads a dummy project if initialization of the project failed
            self.setupModelData(DamProject("", empty=True, **kwargs))

    @timer
    def loadProject(self, proj, **kwargs):

        self.project = proj

        bSuccess = proj.init(**kwargs)
        self.setupModelData(proj)

        if not bSuccess:
            return False

        proj.loadLibraries(noError=True)

        view = self.parent()
        if not view:
            view = self

        damUser = proj.loggedUser()
        sUserName = damUser.loginName if damUser else ""
        sWinTitle = " - ".join(("Davos Browser", labelify(proj.name), sUserName))

        view.setWindowTitle(sWinTitle)

        return bSuccess

    def setupModelData(self, project):

        treeWidget = self.treeWidget

        self.propertyEditorView.disconnectFromTreeWidget()

        treeWidget.setupModelData(project)

        self.propertyEditorView.connectToTreeWidget(treeWidget)
