
import re
import os
import os.path as osp

from PySide.QtGui import QFileDialog

from pytd.gui.itemviews.basecontextmenu import BaseContextMenu
from pytd.gui.dialogs import confirmDialog, promptDialog


from pytd.util.logutils import logMsg
from pytd.util.fsutils import  pathSuffixed, pathJoin
# from pytd.util.logutils import forceLog
from davos.core.drctypes import DrcFile
from pytd.util.sysutils import toStr#, hostApp
from pytd.util.qtutils import setWaitCursor
from davos.core.damtypes import DamAsset
from pytd.util.fsutils import topmostFoundDir
#from fnmatch import fnmatch


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
        { "label":"Publish..."          , "menu": "Main"    , "fnc":self.publishAnything             },

        { "label":"separator"           , "menu": "Main"},
        { "label":"Off"                 , "menu": "Set Lock", "fnc":self.setFilesLocked     , "args":[False]      },
        { "label":"On"                  , "menu": "Set Lock", "fnc":self.setFilesLocked     , "args":[True]       },
        { "label":"Break"               , "menu": "Set Lock", "fnc":self.breakFilesLock     , "dev":True       },

        { "label":"Shotgun Page"        , "menu": "Go To"   , "fnc":self.showShotgunPage                },
        { "label":"Private Location"    , "menu": "Go To"   , "fnc":self.showPrivateLoc                 },
        { "label":"Location"            , "menu": "Go To"   , "fnc":self.showLocation       , "dev":True},

        { "label":"Asset"               , "menu": "Add New" , "fnc":self.createNewAsset     , "dev":True},
        #{ "label":"Files"               , "menu": "Add New" , "fnc":self.publishNewFiles     },
        { "label":"Directory"           , "menu": "Add New" , "fnc":self.createNewDirectory     },


        { "label":"Remove"              , "menu": "Advanced", "fnc":self.removeItems        , "dev":True},
        { "label":"Create Private Dirs" , "menu": "Advanced", "fnc":self.createPrivateDirs  , "dev":True},
        { "label":"Publish Into Shotgun", "menu": "Advanced", "fnc":self.publishSgVersions  , "dev":True},


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
        drcFiles = tuple(item._metaobj for item in itemList)

        for drcFile in drcFiles:
            drcFile.refresh()
            if drcFile.setLocked(False, force=True):
                logMsg('{0} {1}.'.format("Lock broken:", drcFile))

    breakFilesLock.auth_types = ["DrcFile"]

    def publishSgVersions(self, *itemList):

        versionFiles = tuple(item._metaobj for item in itemList)
        self.model()._metamodel.publishSgVersions(versionFiles)

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



    def publishAnything(self, *itemList):

        item = itemList[-1]
        pubEntry = item._metaobj
        proj = self.model()._metamodel

        if isinstance(pubEntry, DrcFile):
            if proj.isEditableResource(pubEntry.absPath()):
                self.__publishEdited(pubEntry)
            else:
                self.__publishRegular(pubEntry)
        else:
            self.__publishFiles(pubEntry)

    #publishAnything.auth_types = ("DrcFile",)

    def __publishEdited(self, pubFile):

        if not isinstance(pubFile, DrcFile):
            raise TypeError('A {} cannot be published.'.format(type(pubFile).__name__))

        sSrcFilePath = self.chooseEditedVersion(pubFile)
        if not sSrcFilePath:
            logMsg("Cancelled !", warning=True)
            return

        proj = self.model()._metamodel
        proj.publishEditedVersion(sSrcFilePath)

    def chooseEditedVersion(self, pubFile):

        privDir = pubFile.getPrivateDir()
        if not privDir:
            raise RuntimeError('Could not find the private directory !')

        sNameFilter = pathSuffixed(pubFile.nextVersionName(), '*').replace(' ', '?')
        sSrcFilePath, _ = QFileDialog.getOpenFileName(self.view,
                                                      "Select a file to publish...",
                                                      privDir.absPath(),
                                                      sNameFilter)
        return sSrcFilePath

    def __publishRegular(self, pubFile):

        sSrcFilePath = self.chooseRegularVersion(pubFile)
        if not sSrcFilePath:
            logMsg("Cancelled !", warning=True)
            return

        pubFile.publishVersion(sSrcFilePath, autoLock=True)

    def chooseRegularVersion(self, pubFile):

        sExt = osp.splitext(pubFile.name)[1]
        if not sExt:
            raise ValueError('File has no extension: {}'.format(pubFile))

        sStartDirPath = osp.dirname(pubFile.sourceFile)
        if not osp.isdir(sStartDirPath):
            sStartDirPath = pubFile.getPrivateDir(weak=True).absPath()
        sStartDirPath = topmostFoundDir(sStartDirPath)

        sSrcFilePath, _ = QFileDialog.getOpenFileName(self.view,
                                                      "Select a file to publish...",
                                                      sStartDirPath,
                                                      "File (*{})".format(sExt))
        return sSrcFilePath

    def __publishFiles(self, pubDir):

        if not pubDir.allowFreePublish():
            confirmDialog(title='SORRY !',
                          message="You can't add new files here.",
                          button=["OK"],
                          icon="information")
            return

        sFilePathList = self.chooseFiles(pubDir)
        if not sFilePathList:
            logMsg("Cancelled !", warning=True)
            return

        for sSrcFilePath in sFilePathList:
            print pubDir.publishFile(sSrcFilePath, autoLock=True, autoUnlock=True)

        pubDir.refresh(children=True)

    def chooseFiles(self, pubDir):

        sStartDirPath = topmostFoundDir(pubDir.getHomonym("private", weak=True).absPath())
        sFilePathList, _ = QFileDialog.getOpenFileNames(self.view,
                                                     "Select files to publish...",
                                                     sStartDirPath,
                                                     "File (*.*)")
        return sFilePathList

    def createNewDirectory(self, *itemList):

        item = itemList[-1]
        pubDir = item._metaobj
        #proj = self.model()._metamodel

        if not pubDir.allowFreePublish():
            confirmDialog(title='SORRY !',
                          message="You can't add new directories here.",
                          button=["OK"],
                          icon="information")
            return

        result = promptDialog(title='Please...',
                            message='Directory Name: ',
                            button=['OK', 'Cancel'],
                            defaultButton='OK',
                            cancelButton='Cancel',
                            dismissString='Cancel',
                            scrollableField=True,
                            )

        if result == 'Cancel':
            logMsg("Cancelled !" , warning=True)
            return

        sDirName = promptDialog(query=True, text=True)
        if not sDirName:
            return

        os.mkdir(pathJoin(pubDir.absPath(), sDirName.strip().replace(" ", "_")))
        pubDir.refresh(children=True)

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

    def showPrivateLoc(self, *itemList):

        item = itemList[-1]
        drcEntry = item._metaobj

        pubDir = drcEntry
        if isinstance(drcEntry, DrcFile):
            pubDir = drcEntry.parentDir()

        privDir = pubDir.getHomonym("private")

        if not privDir:
            confirmDialog(title='SORRY !',
                        message="Private directory not found !",
                        button=["OK"],
                        icon="critical")
            return

        privDir.showInExplorer(select=True)

    def showLocation(self, *itemList):
        item = itemList[-1]
        drcEntry = item._metaobj

        if drcEntry.isPublic():
            sMsg = u"Go to PUBLIC location of {} !?".format(drcEntry.name)
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

        drcEntry.showInExplorer(select=True)

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

        sSection = drcDir.name
        if not proj._confobj.hasSection(sSection):
            raise RuntimeError("No such asset type configured: '{}'."
                               .format(sSection))

        if not proj._confobj.getVar(sSection, "template_dir", ""):
            raise RuntimeError("No template configured for '{}'".format(sSection))

        result = promptDialog(title='Please...',
                            message='Entity Name: ',
                            button=['OK', 'Cancel'],
                            defaultButton='OK',
                            cancelButton='Cancel',
                            dismissString='Cancel',
                            scrollableField=True,
                            text=sSection + "_"
                            )

        if result == 'Cancel':
            logMsg("Cancelled !" , warning=True)
            return

        sEntityName = promptDialog(query=True, text=True)
        if not sEntityName:
            return

        damAst = DamAsset(proj, name=sEntityName, assetType=sSection)
        if damAst.assetType != sSection:
            raise ValueError("Bad asset type: '{}' ! Expected '{}'."
                             .format(damAst.assetType, sSection))

        damAst.createDirsAndFiles(dryRun=False)
        astDir = damAst.getResource("public")
        if astDir:
            astDir.parentDir().refresh(children=True)

    createNewAsset.auth_types = ("DrcDir",)

    def createPrivateDirs(self, *itemList):

        entryList = tuple(item._metaobj for item in itemList)

        for drcDir in entryList:
            drcDir.getHomonym("private", create=True)

    createPrivateDirs.auth_types = ("DrcDir",)

    def logData(self, *itemList):

        for item in itemList:
            item._metaobj.logData()

    def fixNotUpToDate(self, *itemList):

#        proj = self.model()._metamodel

#        if proj.name != "zombtest":
#            raise EnvironmentError("No allowed in project: '{}'".format(proj.name))

        for item in itemList:

            drcFile = item._metaobj
            fsMTime = drcFile.getPrpty("fsMtime")
            drcFile._setPrpty("dbMtime", fsMTime)
            drcFile.refresh()

