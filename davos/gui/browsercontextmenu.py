
from PySide import QtGui

from pytd.gui.itemviews.basecontextmenu import BaseContextMenu
from pytd.gui.dialogs import confirmDialog

# from pytd.util.sysutils import toStr
from pytd.util.logutils import logMsg
from pytd.util.fsutils import  pathSuffixed

# from pytd.util.fsutils import pathNorm
# from pytd.util.logutils import forceLog
from davos.core.drctypes import DrcFile
from pytd.util.sysutils import toStr


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
        { "label":"Edit"                , "menu": "Main"    , "fnc":self.editFile                   },
        #{ "label":"separator"          , "menu": "Main"},
        { "label":"Publish..."          , "menu": "Main"    , "fnc":self.publishEditedVersion       },

        { "label":"separator"           , "menu": "Main"},
        { "label":"Private Directory"   , "menu": "Go To"   , "fnc":self.showPrivateDirInExplorer   },
        #{ "label":"Server Directory"    , "menu": "Go To"   , "fnc":self.exploreItemPath    , "args":["server"]   },
        #{ "label":"Damas Web Page"      , "menu": "Go To"   , "fnc":self.launchItemWebPage                        },

        { "label":"separator"           , "menu": "Main"},
        { "label":"Off"                 , "menu": "Set Lock", "fnc":self.setFilesLocked     , "args":[False]      },
        { "label":"On"                  , "menu": "Set Lock", "fnc":self.setFilesLocked     , "args":[True]       },

        { "label":"Remove"              , "menu": "Advanced", "fnc":self.removeItems        , "dev":True},
        { "label":"Log DbNode"          , "menu": "Advanced", "fnc":self.logDbNodeData      , "dev":True},
        { "label":"Show In Explorer"    , "menu": "Main"    , "fnc":self.showInExplorer      , "dev":True},

        )

        return actionsCfg

    # @forceLog(log='all')
    def editFile(self, *itemList):

        drcFile = itemList[-1]._metaobj

        sMsg = u'Are you sure you want to EDIT this resource: \n\n    ' + drcFile.relPath()

        sConfirm = confirmDialog(title='WARNING !',
                                message=sMsg + u' ?',
                                button=['OK', 'Cancel'],
                                defaultButton='Cancel',
                                cancelButton='Cancel',
                                dismissString='Cancel',
                                icon="warning")

        if sConfirm == 'Cancel':
            logMsg("Cancelled !", warning=True)
            return

        drcFile.edit()

    editFile.auth_types = ("DrcFile",)

    def setFilesLocked(self, bLock, *itemList):

        drcFiles = (item._metaobj for item in itemList)

        sAction = "Lock" if bLock else "Unlock"

        for drcFile in drcFiles:
            drcFile.refresh()
            if drcFile.setLocked(bLock):
                logMsg('{0} {1}.'.format(sAction + "ed", drcFile))

        return True

    setFilesLocked.auth_types = [ "DrcFile" ]


    # @forceLog(log="debug")
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
    def pickupPrivateFileToPublish(drcFile):

        privDir = drcFile.getPrivateDir()
        if not privDir:
            raise RuntimeError, 'Could not find the private directory !'

        sNameFilter = pathSuffixed(drcFile.nextVersionName(), '*').replace(' ', '?')
        sSrcFilePath, _ = QtGui.QFileDialog.getOpenFileName(None,
                                                            "You know what to do...",
                                                            privDir.absPath(),
                                                            sNameFilter
                                                            )

        return sSrcFilePath

    def publishEditedVersion(self, *itemList):

        item = itemList[-1]
        drcFile = item._metaobj

        if type(drcFile) is not DrcFile:
            raise TypeError, 'A {} cannot be published.'.format(type(drcFile).__name__)

        sSrcFilePath = self.__class__.pickupPrivateFileToPublish(drcFile)
        if not sSrcFilePath:
            logMsg("Cancelled !", warning=True)
            return

        proj = self.model()._metamodel

        proj.publishEditedVersion(sSrcFilePath, autoLock=True)

    publishEditedVersion.auth_types = ("DrcFile" ,)

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
