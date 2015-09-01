
import re

from PySide import QtGui

from pytd.gui.itemviews.basecontextmenu import BaseContextMenu
from pytd.gui.dialogs import confirmDialog, promptDialog


from pytd.util.logutils import logMsg
from pytd.util.fsutils import  pathSuffixed
# from pytd.util.logutils import forceLog
from davos.core.drctypes import DrcFile
from pytd.util.sysutils import toStr#, hostApp
from pytd.util.qtutils import setWaitCursor
from davos.core.damtypes import DamAsset


class BrowserContextMenu(BaseContextMenu):

    def __init__(self, parentView):
        super(BrowserContextMenu, self).__init__(parentView)

    def getActionSelection(self):

        view = self.view
        model = view.model()

        selectedItems = BaseContextMenu.getActionSelection(self)
        if not selectedItems:
            viewRootItem = model.itemFromIndex(view.rootIndex())
            if viewRootItem:
                selectedItems.append(viewRootItem)

        return selectedItems

    def getActionsConfig(self):

        # proj = self.model().metamodel

        actionsCfg = (
        { "label":"Refresh"             , "menu": "Main"    , "fnc":self.refreshItems               },

        { "label":"separator"           , "menu": "Main"    , "dev":False                           },
        { "label":"Open"                , "menu": "Main"    , "fnc":self.openFile                   },
        { "label":"Edit"                , "menu": "Main"    , "fnc":self.editFile                   },
        { "label":"Publish..."          , "menu": "Main"    , "fnc":self.publishEditedVersion       },

        { "label":"separator"           , "menu": "Main"},
        { "label":"Private Directory"   , "menu": "Go To"   , "fnc":self.showPrivateDirInExplorer   },
        #{ "label":"Server Directory"    , "menu": "Go To"   , "fnc":self.exploreItemPath    , "args":["server"]   },
        #{ "label":"Damas Web Page"      , "menu": "Go To"   , "fnc":self.launchItemWebPage                        },

        { "label":"separator"           , "menu": "Main"},
        { "label":"Off"                 , "menu": "Set Lock", "fnc":self.setFilesLocked     , "args":[False]      },
        { "label":"On"                  , "menu": "Set Lock", "fnc":self.setFilesLocked     , "args":[True]       },
        { "label":"Break"               , "menu": "Set Lock", "fnc":self.breakFilesLock     , "dev":True       },

        { "label":"Remove"              , "menu": "Advanced", "fnc":self.removeItems        , "dev":True},
        { "label":"Roll Back"            , "menu": "Advanced", "fnc":self.rollBackToVersion , "dev":True},

        { "label":"Create New Asset"    , "menu": "Main"    , "fnc":self.createNewAsset     , "dev":True},
        { "label":"Create Private Dirs" , "menu": "Main"    , "fnc":self.createPrivateDir   , "dev":False},

#        { "label":"Show In Explorer"    , "menu": "Main"    , "fnc":self.showInExplorer     , "dev":True},

        { "label":"Log Data"          , "menu": "Db Node", "fnc":self.logDbNodeData         , "dev":True},
        { "label":"Delete"          , "menu": "Db Node", "fnc":self.deleteDbNode            , "dev":True},
        )

        return actionsCfg

    # @forceLog(log='all')
    def editFile(self, *itemList):

        pubFile = itemList[-1]._metaobj
        pubFile.edit(openFile=True)

    editFile.auth_types = ("DrcFile",)

    def openFile(self, *itemList):
        drcEntry = itemList[-1]._metaobj
        drcEntry.sysOpen()

    openFile.auth_types = ("DrcFile",)

    def setFilesLocked(self, bLock, *itemList):

        drcFiles = (item._metaobj for item in itemList)

        sAction = "Lock" if bLock else "Unlock"

        for drcFile in drcFiles:
            drcFile.refresh()
            if drcFile.setLocked(bLock):
                logMsg('{0} {1}.'.format(sAction + "ed", drcFile))

        return True

    setFilesLocked.auth_types = [ "DrcFile" ]

    def breakFilesLock(self, *itemList):
        drcFiles = (item._metaobj for item in itemList)

        for drcFile in drcFiles:
            drcFile.refresh()
            if drcFile.setLocked(False, force=True):
                logMsg('{0} {1}.'.format("Lock broken:", drcFile))

    breakFilesLock.auth_types = [ "DrcFile" ]

    @setWaitCursor
    def refreshItems(self, *itemList, **kwargs):

        for item in itemList:
            item._metaobj.refresh(children=True)

#         proj = self.model()._metamodel
#         for lib in proj.loadedLibraries.itervalues():
#             print ""
#             for d in lib._cachedEntries.iteritems():
#                 print d

    # @forceLog(log="debug")
    def removeItems(self, *itemList):

        entryList = tuple(item._metaobj for item in itemList)

        sEntryList = "\n    " .join(entry.name for entry in entryList)

        sMsg = u'Are you sure you want to DELETE these resources: \n\n    ' + sEntryList

        sConfirm = confirmDialog(title='WARNING !',
                                 message=sMsg,
                                 button=['OK', 'Cancel'],
                                 defaultButton='Cancel',
                                 cancelButton='Cancel',
                                 dismissString='Cancel',
                                 icon="warning")

        if sConfirm == 'Cancel':
            logMsg("Cancelled !", warning=True)
            return

        for entry in entryList:

            try:
                entry.sendToTrash()
            except Exception, e:
                sResult = confirmDialog(title='SORRY !',
                                        message=toStr(e),
                                        button=["Continue", "Abort"],
                                        defaultButton="Continue",
                                        cancelButton="Abort",
                                        dismissString="Abort",
                                        icon="critical")

                if sResult == "Abort":
                    return
                else:
                    continue


    @staticmethod
    def choosePrivateFileToPublish(drcFile):

        privDir = drcFile.getPrivateDir()
        if not privDir:
            raise RuntimeError('Could not find the private directory !')

        sNameFilter = pathSuffixed(drcFile.nextVersionName(), '*').replace(' ', '?')
        sSrcFilePath, _ = QtGui.QFileDialog.getOpenFileName(None,
                                                            "Select a file to publish...",
                                                            privDir.absPath(),
                                                            sNameFilter
                                                            )

        return sSrcFilePath

    def publishEditedVersion(self, *itemList):

        item = itemList[-1]
        drcFile = item._metaobj

        if not isinstance(drcFile, DrcFile):
            raise TypeError, 'A {} cannot be published.'.format(type(drcFile).__name__)

        sSrcFilePath = self.__class__.choosePrivateFileToPublish(drcFile)
        if not sSrcFilePath:
            logMsg("Cancelled !", warning=True)
            return

        proj = self.model()._metamodel
        proj.publishEditedVersion(sSrcFilePath)

    publishEditedVersion.auth_types = ("DrcFile",)

    def rollBackToVersion(self, *itemList):

        item = itemList[-1]
        drcFile = item._metaobj
        drcFile.refresh()

        v = drcFile.currentVersion - 1

        sMsg = u"Restore version {} of '{}' ??".format(v, drcFile.name)

        sConfirm = confirmDialog(title='WARNING !',
                                 message=sMsg,
                                 button=['OK', 'Cancel'],
                                 defaultButton='Cancel',
                                 cancelButton='Cancel',
                                 dismissString='Cancel',
                                 icon="warning")

        if sConfirm == 'Cancel':
            logMsg("Cancelled !", warning=True)
            return

        drcFile.rollBackToVersion(v)

    publishEditedVersion.auth_types = ("DrcFile",)

    def showPrivateDirInExplorer(self, *itemList):

        item = itemList[-1]
        drcEntry = item._metaobj

        if isinstance(drcEntry, DrcFile):
            privDir = drcEntry.parentDir().getHomonym("private")
        else:
            privDir = drcEntry.getHomonym("private")

        if not privDir:
            confirmDialog(title='SORRY !',
                        message="Private directory not found !",
                        button=["OK"],
                        icon="critical")
            return

        privDir.showInExplorer()

    def showInExplorer(self, *itemList):
        item = itemList[-1]
        drcEntry = item._metaobj

        drcEntry.showInExplorer()

    def logDbNodeData(self, *itemList):

        for item in itemList:
            item._metaobj._dbnode.logData()

    def deleteDbNode(self, *itemList):

        dbNodeList = []
        msg = ""
        for item in itemList:
            dbNode = item._metaobj._dbnode
            if dbNode:
                r = dbNode.dataRepr("file")
                r = re.sub(r"[\s{}]", "", r)
                msg += (r + "\n")
                dbNodeList.append(dbNode)

        sMsg = u'Are you sure you want to DELETE these db nodes:\n\n' + msg

        sConfirm = confirmDialog(title='WARNING !',
                                 message=sMsg,
                                 button=['OK', 'Cancel'],
                                 defaultButton='Cancel',
                                 cancelButton='Cancel',
                                 dismissString='Cancel',
                                 icon="warning")

        if sConfirm == 'Cancel':
            logMsg("Cancelled !", warning=True)
            return

        for dbNode in dbNodeList:
            dbNode.delete()

    def createNewAsset(self, *itemList):

        item = itemList[-1]
        drcDir = item._metaobj
        proj = drcDir.library.project

        sSection = drcDir.fileName()

        if not proj.hasVar(sSection, "template_dir"):
            raise RuntimeError("No template found for '{}'".format(sSection))

        result = promptDialog(title='Please...',
                            message='Entity Name: ',
                            button=['OK', 'Cancel'],
                            defaultButton='OK',
                            cancelButton='Cancel',
                            dismissString='Cancel',
                            scrollableField=True,
                            )

        if result == 'Cancel':
            logMsg("Cancelled !" , warning=True)
            return

        sEntityName = promptDialog(query=True, text=True)
        if not sEntityName:
            return

        damAst = DamAsset(proj, name=sEntityName, assetType=sSection)
        damAst.createDirsAndFiles()

    createNewAsset.auth_types = ("DrcDir",)

    def createPrivateDir(self, *itemList):

        entryList = tuple(item._metaobj for item in itemList)

        for drcDir in entryList:
            drcDir.getHomonym("private", create=True)

    createPrivateDir.auth_types = ("DrcDir",)


