
import re
import os.path as osp

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
from pytd.util.fsutils import topmostFoundDir


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
        { "label":"View (Read-only)"    , "menu": "Main"    , "fnc":self.openFile                   },
        { "label":"Edit"                , "menu": "Main"    , "fnc":self.editFile                   },
        { "label":"Publish..."          , "menu": "Main"    , "fnc":self.publishVersion             },

        { "label":"separator"           , "menu": "Main"},
        { "label":"Off"                 , "menu": "Set Lock", "fnc":self.setFilesLocked     , "args":[False]      },
        { "label":"On"                  , "menu": "Set Lock", "fnc":self.setFilesLocked     , "args":[True]       },
        { "label":"Break"               , "menu": "Set Lock", "fnc":self.breakFilesLock     , "dev":True       },

        { "label":"Private Directory"   , "menu": "Go To"   , "fnc":self.showPrivateDirInExplorer   },
        { "label":"Shotgun Page"        , "menu": "Go To"   , "fnc":self.showShotgunPage   },

        { "label":"Asset"               , "menu": "Add New"    , "fnc":self.createNewAsset     , "dev":True},
        { "label":"File"                , "menu": "Add New"    , "fnc":self.publishNewFile     , "dev":True},

        { "label":"Remove"              , "menu": "Advanced", "fnc":self.removeItems        , "dev":True},

        { "label":"separator"           , "menu": "Main"},
        { "label":"Log Data"            , "menu": "DrcEntry", "fnc":self.logData            , "dev":True},
        { "label":"Fix Not Up-to-date"  , "menu": "DrcEntry", "fnc":self.fixNotUpToDate     , "dev":True},

        { "label":"Log Data"            , "menu": "DbNode", "fnc":self.logDbNodeData       , "dev":True},
        { "label":"Delete"              , "menu": "DbNode", "fnc":self.deleteDbNode        , "dev":True},
        )

        return actionsCfg


    def editFile(self, *itemList):

        pubFile = itemList[-1]._metaobj
        pubFile.edit(openFile=True, existing="choose")

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

    setFilesLocked.auth_types = ["DrcFile"]

    def breakFilesLock(self, *itemList):
        drcFiles = (item._metaobj for item in itemList)

        for drcFile in drcFiles:
            drcFile.refresh()
            if drcFile.setLocked(False, force=True):
                logMsg('{0} {1}.'.format("Lock broken:", drcFile))

    breakFilesLock.auth_types = ["DrcFile"]

    @setWaitCursor
    def refreshItems(self, *itemList, **kwargs):

        for item in itemList:
            item._metaobj.refresh(children=True)

#         proj = self.model()._metamodel
#         for lib in proj.loadedLibraries.itervalues():
#             print ""
#             for d in lib._cachedEntries.iteritems():
#                 print d

        return

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

    def publishNewFile(self, *itemList):

        item = itemList[-1]
        pubDir = item._metaobj
        #proj = self.model()._metamodel

        sSrcFilePath = self.__class__.chooseNewFile(pubDir)
        if not sSrcFilePath:
            logMsg("Cancelled !", warning=True)
            return

        print pubDir.publishFile(sSrcFilePath, autoLock=True, autoUnlock=True)

    publishNewFile.auth_types = ("DrcDir",)

    @staticmethod
    def chooseNewFile(pubDir):

        sStartDirPath = topmostFoundDir(pubDir.getHomonym("private", weak=True).absPath())
        sSrcFilePath, _ = QtGui.QFileDialog.getOpenFileName(None,
                                                            "Select a file to publish...",
                                                            sStartDirPath,
                                                            "File (*.*)")
        return sSrcFilePath

    def publishVersion(self, *itemList):

        item = itemList[-1]
        pubEntry = item._metaobj
        proj = self.model()._metamodel

        if proj.isEditableResource(pubEntry.absPath()):
            self.__publishEdited(pubEntry)
        else:
            self.__publishRegular(pubEntry)

    publishVersion.auth_types = ("DrcFile",)

    def __publishEdited(self, pubFile):

        if not isinstance(pubFile, DrcFile):
            raise TypeError('A {} cannot be published.'.format(type(pubFile).__name__))

        sSrcFilePath = self.__class__.chooseEditedVersion(pubFile)
        if not sSrcFilePath:
            logMsg("Cancelled !", warning=True)
            return

        proj = self.model()._metamodel
        proj.publishEditedVersion(sSrcFilePath)

    @staticmethod
    def chooseEditedVersion(pubFile):

        privDir = pubFile.getPrivateDir()
        if not privDir:
            raise RuntimeError('Could not find the private directory !')

        sNameFilter = pathSuffixed(pubFile.nextVersionName(), '*').replace(' ', '?')
        sSrcFilePath, _ = QtGui.QFileDialog.getOpenFileName(None,
                                                            "Select a file to publish...",
                                                            privDir.absPath(),
                                                            sNameFilter)
        return sSrcFilePath

    def __publishRegular(self, pubFile):

        sSrcFilePath = self.__class__.chooseRegularVersion(pubFile)
        if not sSrcFilePath:
            logMsg("Cancelled !", warning=True)
            return

        pubFile.publishVersion(sSrcFilePath, autoLock=True)

    @staticmethod
    def chooseRegularVersion(pubFile):

        sExt = osp.splitext(pubFile.name)[1]
        if not sExt:
            raise ValueError, 'File has no extension: {}'.format(pubFile)

        sStartDirPath = osp.dirname(pubFile.sourceFile)
        if not osp.isdir(sStartDirPath):
            sStartDirPath = pubFile.getPrivateDir(weak=True).absPath()
        sStartDirPath = topmostFoundDir(sStartDirPath)

        sSrcFilePath, _ = QtGui.QFileDialog.getOpenFileName(None,
                                                            "Select a file to publish...",
                                                            sStartDirPath,
                                                            "File (*{})".format(sExt))
        return sSrcFilePath

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

    def showShotgunPage(self, *itemList):

        item = itemList[-1]
        drcEntry = item._metaobj

        damEntity = drcEntry.getEntity(fail=True)
        damEntity.showShotgunPage()

    def showPrivateDirInExplorer(self, *itemList):

        item = itemList[-1]
        drcEntry = item._metaobj

        pubDir = drcEntry
        if isinstance(drcEntry, DrcFile):
            pubDir = drcEntry.parentDir()

        if drcEntry.isPrivate():
            privDir = pubDir
        else:
            privDir = pubDir.getHomonym("private")

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

        entryList = []
        msg = ""
        for item in itemList:
            entry = item._metaobj
            dbNode = entry._dbnode
            if dbNode:
                r = dbNode.dataRepr("file")
                r = re.sub(r"[\s{}]", "", r)
                msg += (r + "\n")
                entryList.append(entry)

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

        for entry in entryList:
            entry.deleteDbNode()

    def createNewAsset(self, *itemList):

        item = itemList[-1]
        drcDir = item._metaobj

        library = drcDir.library
        if library.sectionName != "asset_lib":
            raise RuntimeError("Cannot create new asset under '{}'"
                               .format(library.sectionName))

        proj = library.project

        sSection = drcDir.fileName()
        if not proj._confobj.hasSection(sSection):
            raise RuntimeError("Cannot create new asset under '{}'"
                               .format(sSection))

        if not proj._confobj.hasVar(sSection, "template_dir"):
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
        astDir = damAst.getResource("public")
        if astDir:
            astDir.parentDir().refresh(children=True)

    createNewAsset.auth_types = ("DrcDir",)

    def createPrivateDir(self, *itemList):

        entryList = tuple(item._metaobj for item in itemList)

        for drcDir in entryList:
            drcDir.getHomonym("private", create=True)

    createPrivateDir.auth_types = ("DrcDir",)

    def logData(self, *itemList):

        for item in itemList:
            item._metaobj.logData()

    def fixNotUpToDate(self, *itemList):

        proj = self.model()._metamodel

        if proj.name != "zombtest":
            raise EnvironmentError("No allowed in project: '{}'".format(proj.name))

        for item in itemList:

            drcFile = item._metaobj
            fsMTime = drcFile.getPrpty("fsMtime")
            drcFile._setPrpty("dbMtime", fsMTime)
            drcFile.refresh()

