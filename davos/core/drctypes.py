
import os
import os.path as osp
import re
from datetime import datetime
import filecmp

from PySide.QtCore import QDir

from pytd.gui.dialogs import confirmDialog

from pytd.util.logutils import logMsg, forceLog
from pytd.util.qtutils import toQFileInfo
from pytd.util.fsutils import pathJoin, pathSuffixed, pathRel, normCase
from pytd.util.fsutils import copyFile
from pytd.util.fsutils import sha1HashFile
from pytd.util.qtutils import setWaitCursor
from pytd.util.strutils import padded
from pytd.util.external.send2trash import send2trash

from .properties import DrcMetaObject
from .properties import DrcEntryProperties, DrcFileProperties
from .utils import promptForComment
from .utils import versionFromName
from .locktypes import LockFile
from pytd.util.sysutils import timer, getCaller


class DrcEntry(DrcMetaObject):

    classUiPriority = 0

    propertiesDctItems = DrcEntryProperties
    propertiesDct = dict(propertiesDctItems)

    # defines which property will be displayed as a Tree in UI.
    primaryProperty = propertiesDctItems[0][0]


    def __init__(self, drcLibrary, absPathOrInfo=None, **kwargs):

        self.library = drcLibrary
        self._qfileinfo = None
        self._qdir = None
        self._dbnode = None

        self.loadedChildren = []
        self.childrenLoaded = False

        super(DrcEntry, self).__init__()

        fileInfo = toQFileInfo(absPathOrInfo)
        if fileInfo:

            if id(self) != id(drcLibrary):
                sAbsPath = fileInfo.filePath()
                if not drcLibrary.contains(fileInfo.absoluteFilePath()):
                    msg = u"Path is NOT part of {}: '{}'".format(drcLibrary, sAbsPath)
                    raise AssertionError(msg)

            self.loadData(fileInfo, **kwargs)

    def loadData(self, fileInfo, **kwargs):

        fileInfo.setCaching(True)

        curFileinfo = self._qfileinfo
        bRefreshing = ((curFileinfo is not None) and (curFileinfo == fileInfo))
        if bRefreshing:
            curFileinfo.refresh()
            self._qdir.refresh()
        else:
            self._qfileinfo = fileInfo
            sAbsPath = fileInfo.absoluteFilePath()

            self._qdir = QDir(sAbsPath)
            self._qdir.setFilter(QDir.NoDotAndDotDot | QDir.Dirs | QDir.Files)

            if self.isPublic():
                bFindDbNode = kwargs.get('dbNode', False)
                self._dbnode = self.getDbNode(find=bFindDbNode)

        super(DrcEntry, self).loadData()

        sEntryName = self.name
        self.baseName, self.suffix = osp.splitext(sEntryName)
        self.label = sEntryName

        #print self, self._dbnode.logData() if self._dbnode else "Rien du tout"
        if not bRefreshing:
            self._remember()

        fileInfo.setCaching(False)

    def parentDir(self):
        return self.library.getEntry(self.relDirPath())

    def refresh(self, **kwargs):
        logMsg(log="all")

        if self._writingValues_:
            return

        logMsg('Refreshing : {0}'.format(self), log='debug')

        bDbNode = kwargs.get("dbNode", True)
        bChildren = kwargs.get("children", False)
        parent = kwargs.get("parent", None)

        fileInfo = self._qfileinfo

        if not fileInfo.exists():
            self._forget(parent=parent, recursive=True)
        else:
            self.loadData(fileInfo)
            if bDbNode and self._dbnode:
                self._dbnode.refresh()
            self.updateModelRow()

            if bChildren and self.childrenLoaded:

                oldChildren = self.loadedChildren[:]

                for child in self.iterChildren():
                    if child not in oldChildren:
                        child.addModelRow(self)
                        self.loadedChildren.append(child)

                for child in oldChildren:
                    child.refresh(children=bChildren, parent=self, dbNode=False)

    def isPublic(self):
        return self.library.space == "public"

    def isPrivate(self):
        return self.library.space == "private"

    def getChild(self, sChildName):
        return self.library.getEntry(pathJoin(self.absPath(), sChildName))

    def iterChildren(self, *nameFilters, **kwargs):

        if self.isPublic():
            self.loadChildDbNodes()

        getEntry = self.library.getEntry
        return (getEntry(info) for info in self._qdir.entryInfoList(nameFilters, **kwargs))

    def hasChildren(self):
        return False

    def absDirPath(self):
        return self._qfileinfo.absolutePath()

    def relDirPath(self):
        return self.library.relFromAbsPath(self.absDirPath())

    def absPath(self):
        return self._qfileinfo.absoluteFilePath()

    def relPath(self):
        return self.library.relFromAbsPath(self.absPath())

    def relFromAbsPath(self, sAbsPath):
        return pathRel(sAbsPath, self.absPath())

    def damasPath(self):
        sLibPath = self.library.absPath()
        sLibDmsPath = self.library.getVar("damas_path")
        return re.sub('^' + sLibPath, sLibDmsPath, self.absPath())

    #@forceLog(log='debug')
    def getDbNode(self, create=False, find=False):

        assert self.isPublic(), "File is NOT public !"

        _cachedDbNodes = self.library._cachedDbNodes
        sRelPath = normCase(self.relPath())

        logMsg(u"\ngetting DbNode: '{}'".format(sRelPath), log='debug')
        dbnode = _cachedDbNodes.get(sRelPath)
        if dbnode:
            logMsg(u"got from CACHE.", log='debug')
        elif find:
            sParentDirPath, sEntryName = osp.split(sRelPath)
            data = {
                    "project":self.library.project.name,
                    "library":self.library.fullName,
                    "parentDir": sParentDirPath,
                    "name":sEntryName,
                    }
            sQuery = " ".join("{}:{}".format(k, v) for k, v in data.iteritems())
            print sQuery
            dbnode = self.library._db.findOne(sQuery)
            if dbnode:
                logMsg(u"got from DB.", log='debug')
                _cachedDbNodes[sRelPath] = dbnode

        if (not dbnode) and create:
            dbnode = self.createDbNode()
            logMsg(u"just created.", log='debug')
        else:
            logMsg(u"not found.", log='debug')

        return dbnode

    def createDbNode(self):

        assert self.isPublic(), "File is NOT public !"

        print u"creating DbNode for {}".format(self)
        data = self._initialDbNodeData()

        _cachedDbNodes = self.library._cachedDbNodes

        cacheKey = pathJoin(data.get("parentDir"), data.get("name"))
        if cacheKey in _cachedDbNodes:
            raise RuntimeError("DbNode already created: '{}'".format(cacheKey))

        dbnode = self.library._db.createNode(data)
        print u"storing DbNode:", cacheKey
        _cachedDbNodes[cacheKey] = dbnode

        return dbnode

    #@timer
    def loadChildDbNodes(self):

        _cachedDbNodes = self.library._cachedDbNodes

        for dbnode in self.getChildDbNodes():

            cacheKey = pathJoin(dbnode.getValue("parentDir"), dbnode.getValue("name"))
            cachedNode = _cachedDbNodes.get(cacheKey)
            if cachedNode:
                cachedNode.refresh(dbnode._data)
            else:
                #print u"loading DbNode:", cacheKey, dbnode.dataRepr()
                _cachedDbNodes[cacheKey] = dbnode

    def getChildDbNodes(self, **kwargs):

        data = {
                "library":self.library.fullName,
                "parentDir": normCase(self.relPath()),
                }

        sQuery = " ".join(u"{}:{}".format(k, v) for k, v in data.iteritems())
        return self.library._db.findNodes(sQuery, **kwargs)

    #@timer
    def loadChildren(self):

        self.childrenLoaded = True

        for child in self.iterChildren():
            child.addModelRow(self)
            self.loadedChildren.append(child)

    def addModelRow(self, parent):

        model = self.library._itemmodel
        if not model:
            return

        parentPrpty = parent.metaProperty(model.primaryProperty)

        for parentItem in parentPrpty.viewItems:
            model.loadRowItems(self, parentItem)

    def delModelRow(self):

        model = self.library._itemmodel
        primePrpty = self.metaProperty(model.primaryProperty)

        for primeItem in primePrpty.viewItems:

            parentItem = primeItem.parent()
            parentItem.removeRow(primeItem.row())

        primePrpty.viewItems = []

    def updateModelRow(self):
        logMsg(log='all')

        model = self.library._itemmodel
        if not model:
            return

        primePrpty = self.metaProperty(model.primaryProperty)
        for primeItem in primePrpty.viewItems:
            primeItem.updateRow()

    def getIconData(self):
        return self._qfileinfo


    def sendToTrash(self):
        send2trash(self.absPath())
        self.refresh(children=True)

    def _initialDbNodeData(self):

        return {
                "project":self.library.project.name,
                "library":self.library.fullName,
                "parentDir": normCase(self.relDirPath()),
                "name":normCase(self.name),
                }

    def _writeAllValues(self, propertyNames=None):

        sPropertyList = tuple(self.__class__._iterPropertyArg(propertyNames))

        print getCaller(), "sPropertyList", sPropertyList

        sDbNodePrptySet = set(self.filterPropertyNames(sPropertyList,
                                                       accessor="_dbnode"))

        sOtherPrptySet = set(sPropertyList) - sDbNodePrptySet
        print "sOtherPrptySet", sOtherPrptySet

        DrcMetaObject._writeAllValues(self, propertyNames=sOtherPrptySet)

        print "sDbNodePrptySet", sDbNodePrptySet
        data = self.getAllValues(sDbNodePrptySet)
        print "Writing data:", data, self
        self.getDbNode(create=True).setData(data)

    def _remember(self):

        key = self.relPath()
        # print '"{}"'.format(self.relPath())
        _cachedEntries = self.library._cachedEntries

        if key in _cachedEntries:
            logMsg("Already cached: {0}.".format(self), log="debug")
        else:
            logMsg("Caching: {0}.".format(self), log="debug")
            _cachedEntries[key] = self

    def _forget(self, parent=None, **kwargs):
        logMsg(self.__class__.__name__, log='all')

        bRecursive = kwargs.get("recursive", True)

        self.__forgetOne(parent)

        if bRecursive:
            for child in self.loadedChildren[:]:
                child._forget(parent, **kwargs)

    def __forgetOne(self, parent=None):

        key = self.relPath()
        _cachedEntries = self.library._cachedEntries

        if key not in _cachedEntries:
            logMsg("Already dropped: {0}.".format(self), log="debug")
        else:
            parentDir = parent if parent else self.parentDir()
            if parentDir and parentDir.loadedChildren:
                logMsg("Dropping {} from {}".format(self, parentDir), log="debug")
                parentDir.loadedChildren.remove(self)

            del self.loadedChildren[:]
            self.delModelRow()

            return _cachedEntries.pop(key)

    def __getattr__(self, sAttrName):

        sAccessor = '_qfileinfo'

        if (sAttrName == sAccessor) and  not hasattr(self, sAccessor):
            s = "'{}' object has no attribute '{}'.".format(type(self).__name__, sAttrName)
            raise AttributeError(s)

        accessor = getattr(self, sAccessor)
        if hasattr(accessor, sAttrName):
            return getattr(accessor, sAttrName)
        else:
            s = "'{}' object has no attribute '{}'.".format(type(self).__name__, sAttrName)
            raise AttributeError(s)

    def __cmp__(self, other):

        if not isinstance(other, self.__class__):
            return cmp(1 , None)

        return cmp(self.absPath() , other.absPath())


class DrcDir(DrcEntry):

    classUiPriority = 1

    def __init__(self, drcLibrary, absPathOrInfo=None, **kwargs):
        super(DrcDir, self).__init__(drcLibrary, absPathOrInfo, **kwargs)

    def getHomonym(self, sSpace, create=False):

        curLib = self.library
        homoLib = curLib.getHomonym(sSpace)

        sHomoLibPath = homoLib.absPath()
        sHomoPath = re.sub("^" + curLib.absPath(), sHomoLibPath, self.absPath())

        if not osp.exists(sHomoPath) and create:
            os.makedirs(sHomoPath)

        return homoLib.getEntry(sHomoPath)

    def suppress(self):
        parentDir = self.parentDir()
        if parentDir._qdir.rmdir(self.name):
            self.refresh(children=True, parent=parentDir)

    def hasChildren(self):
        return True


class DrcFile(DrcEntry):

    classUiPriority = 2

    propertiesDctItems = DrcFileProperties
    propertiesDct = dict(propertiesDctItems)

    def __init__(self, drcLibrary, absPathOrInfo=None, **kwargs):
        super(DrcFile, self).__init__(drcLibrary, absPathOrInfo, **kwargs)

        self.publishAsserted = False
        self.__savedLockState = None

    def loadData(self, fileInfo, **kwargs):

        sLogin = self.library.project.getLoggedUser().loginName
        self._lockobj = LockFile(fileInfo.absoluteFilePath(), sLogin)

        DrcEntry.loadData(self, fileInfo, **kwargs)

        self.updateCurrentVersion()

    def updateCurrentVersion(self):

        iVers = versionFromName(self.name)
        if iVers is None:
            iVers = self.latestBackupVersion()
        self.currentVersion = iVers

    def edit(self):
        logMsg(log='all')

        self.refresh()

        bLockState = self.getPrpty("locked")
        if not self.setLocked(True):
            return

        try:
            self.makePrivateCopy()
        except:
            self.setLocked(bLockState)
            raise

    def makePrivateCopy(self, **kwargs):

        assert self.isFile(), "File does NOT exist !"
        assert self.isPublic(), "File is NOT public !"
        assert versionFromName(self.name) is None, "File is already a version !"

        pubDir = self.parentDir()
        privDir = pubDir.getHomonym('private', create=True)

        sPrivDirPath = privDir.absPath()

        # adding version suffixes to filename
        sVersionedName = self.nextVersionName()
        sPrivFilenameWithExt = pathSuffixed(sVersionedName, '.', padded(0))

        # at this point, file path is fully converted to private space
        sPrivFilePath = pathJoin(sPrivDirPath, sPrivFilenameWithExt)

        sPubFilePath = self.absPath()
        # now let's make the private copy of that file
        if sPubFilePath == sPrivFilePath:
            raise ValueError('Path of source and destination files are identical: "{0}".'
                             .format(sPubFilePath))

        bForce = kwargs.pop("force", False)
        bDryRun = kwargs.get("dry_run", False)

        if not osp.exists(sPrivDirPath):
            if not bDryRun:
                os.makedirs(sPrivDirPath)

        bSameFiles = False

        if (not bForce) and osp.exists(sPrivFilePath):

            bSameFiles = filecmp.cmp(sPubFilePath, sPrivFilePath, shallow=True)

            if not bSameFiles:

                privFileTime = datetime.fromtimestamp(osp.getmtime(sPrivFilePath))
                pubFileTime = datetime.fromtimestamp(osp.getmtime(sPubFilePath))

                sState = "an OLDER" if privFileTime < pubFileTime else "a NEWER"

                sMsg = """
You have {0} version of '{1}':

    private file: {2}
    public  file: {3}
""".format(sState, sPrivFilenameWithExt,
           privFileTime.strftime("%A, %d-%m-%Y %H:%M"),
           pubFileTime.strftime("%A, %d-%m-%Y %H:%M"),
           )
                sConfirm = confirmDialog(title='WARNING !'
                                        , message=sMsg.strip('\n')
                                        , button=[ 'Keep', 'Overwrite', 'Cancel']
                                        , icon="warning")

                if sConfirm == 'Cancel':
                    logMsg("Cancelled !", warning=True)
                    return ""
                elif sConfirm == 'Keep':
                    return sPrivFilePath

        if bSameFiles:
            logMsg('\nAlready copied "{0}" \n\t to: "{1}"'.format(sPubFilePath, sPrivFilePath))
        else:
            # logMsg('\nCoping "{0}" \n\t to: "{1}"'.format(sPubFilePath, sPrivFilePath))
            copyFile(sPubFilePath, sPrivFilePath, **kwargs)

        return sPrivFilePath

    def differsFrom(self, sOtherFilePath):

        sOtherSha1Key = ""

        sCurFilePath = self.absPath()

        if osp.normcase(sOtherFilePath) == osp.normcase(sCurFilePath):
            return False, sOtherSha1Key

        sOwnSha1Key = self.getPrpty("checksum")
        if not sOwnSha1Key:
            return True, sOtherSha1Key

        sOtherSha1Key = sha1HashFile(sOtherFilePath)
        bDiffers = (sOtherSha1Key != sOwnSha1Key)

        return bDiffers, sOtherSha1Key

    def getPublicFile(self):

        assert self.isFile(), "File does NOT exist !"
        assert self.isPrivate(), "File must live in a PRIVATE library !"

        privDir = self.parentDir()
        pubDir = privDir.getHomonym('public')

        sPrivFilename , sExt = osp.splitext(self.name)

        sPubDirPath = pubDir.absPath()
        sPubFilename = sPrivFilename.split('-v')[0] + sExt
        sPubFilePath = pathJoin(sPubDirPath, sPubFilename)

        return pubDir.library.getEntry(sPubFilePath)

    def getPrivateDir(self):

        assert self.isFile(), "File does NOT exist !"
        assert self.isPublic(), "File is NOT public !"

        pubDir = self.parentDir()
        privDir = pubDir.getHomonym("private")
        return privDir

    def latestBackupVersion(self):
        backupFile = self.getLatestBackupFile()
        return versionFromName(backupFile.name) if backupFile else 0

    def getLatestBackupFile(self):

        backupDir = self.getBackupDir()
        if not backupDir:
            return None

        sNameFilter = pathSuffixed(self.name, '*')
        sEntryList = backupDir._qdir.entryList((sNameFilter,),
                                               filters=QDir.Files,
                                               sort=(QDir.Name | QDir.Reversed))

        if not sEntryList:
            return None

        sFilePath = pathJoin(backupDir.absPath(), sEntryList[0])
        return self.library.getEntry(sFilePath, dbNode=True)


    def assertFilePublishable(self, privFile):

        assert privFile.isPrivate(), "File must live in a PRIVATE library !"

        iSrcVers = versionFromName(privFile.name)
        iNxtVers = self.latestBackupVersion() + 1

        if iSrcVers < iNxtVers:
            raise AssertionError, "File version is OBSOLETE !"
        elif iSrcVers > iNxtVers:
            raise AssertionError, "File version is WHAT THE FUCK !"

        privFile.publishAsserted = True

    @setWaitCursor
    def incrementVersion(self, srcFile, **kwargs):

        if not srcFile.publishAsserted:
            srcFile.publishAsserted = False
            raise RuntimeError("DrcFile.assertFilePublishable() has not been applied to {} !"
                               .format(srcFile))

        bAutoUnlock = kwargs.pop("autoUnlock", False)
        bSaveSha1Key = kwargs.pop("saveSha1Key", False)

        self.saveLockState()

        sSrcFilePath = srcFile.absPath()

        bDiffers, sSrcSha1Key = self.differsFrom(sSrcFilePath)
        if not bDiffers:
            logMsg("Skipping {0} increment: Files are identical.".format(self))
            return True

        backupFile = None

        try:
            sComment, _ = self.beginPublish(**kwargs)
        except RuntimeError, e:
            self.abortPublish(e, backupFile, bAutoUnlock)
            raise

        try:
            copyFile(sSrcFilePath, self.absPath())
        except Exception, e:
            self.abortPublish(e, backupFile, bAutoUnlock)
            raise

        #save the current version that will be incremented in endPublish
        #in case we need to do a rollback on Exception
        iSavedVers = self.currentVersion
        try:
            self.endPublish(sSrcFilePath, sComment,
                            saveSha1Key=bSaveSha1Key,
                            sha1Key=sSrcSha1Key,
                            autoUnlock=bAutoUnlock)
        except Exception, e:
            self.abortPublish(e, backupFile, bAutoUnlock)
            self.rollBackToVersion(iSavedVers)
            raise

        return True

    def beginPublish(self, **kwargs):

        sComment = kwargs.pop("comment", "")

        bLockState = self.savedLockState()

        if not kwargs.pop("autoLock", False):

            if not bLockState:

                msg = u'"{0}" is not locked !'.format(self.name)

                confirmDialog(title='SORRY !'
                            , message=msg
                            , button=["OK"]
                            , defaultButton="OK"
                            , cancelButton="OK"
                            , dismissString="OK")

                raise RuntimeError, msg

        if not self.setLocked(True):
            raise RuntimeError, "Could not lock the file !"


        if not sComment:
            sComment = promptForComment(text=self.getPrpty("comment"))

            if not sComment:
                self.setLocked(bLockState)
                raise RuntimeError, "Comment has NOT been provided !"


        backupFile = None
        version = self.latestBackupVersion()
        if version == 0:
            backupFile = self._weakBackupFile(version)
            if not backupFile.exists():
                backupFile.createFromFile(self)

        self.currentVersion = version

        return sComment, backupFile

    def endPublish(self, sSrcFilePath, sComment, autoUnlock=False,
                   saveSha1Key=False,
                   sha1Key=""):

        self.setPrpty("comment", sComment, write=False)

        if saveSha1Key:
            if not sha1Key:
                sNewSha1Key = sha1HashFile(sSrcFilePath)
            else:
                sNewSha1Key = sha1Key

            self.setPrpty("checksum", sNewSha1Key, write=False)

        self.setPrpty("sourceFile", sSrcFilePath, write=False)

        iNextVers = self.currentVersion + 1
        self.setPrpty("currentVersion", iNextVers, write=False)

        self.writeAllValues()

        backupFile = self.createBackupFile(iNextVers)
        if not backupFile:
            raise RuntimeError, "Could not create backup file !"

        self.restoreLockState(autoUnlock)

    def abortPublish(self, sErrorMsg, backupFile=None, autoUnlock=False):

        if backupFile:

            sBkupFilePath = backupFile.absPath()
            sCurFilePath = self.absPath()
            bSameFiles = filecmp.cmp(sCurFilePath, sBkupFilePath, shallow=True)
            if not bSameFiles:
                copyFile(sBkupFilePath, sCurFilePath)

            backupFile.suppress()

        self.restoreLockState(autoUnlock)

        sMsg = "Publishing aborted: {0}".format(sErrorMsg)
        logMsg(sMsg , warning=True)

        return False

    def savedLockState(self):

        bLockState = self.__savedLockState
        if bLockState is not None:
            return bLockState

        return self.saveLockState()

    def saveLockState(self):

        self.refresh()
        bLockState = self.getPrpty("locked")

        self.__savedLockState = bLockState

        return bLockState

    def restoreLockState(self, autoUnlock=False):

        bLockSate = self.__savedLockState

        if autoUnlock:
            self.setLocked(False)
        elif bLockSate is not None:
            self.setLocked(bLockSate)

        self.__savedLockState = None

        self.refresh()

    def createBackupFile(self, version):

        backupFile = self._weakBackupFile(version)
        if backupFile.exists():
            raise RuntimeError("Backup file ALREADY exists: \n\t> '{}'"
                               .format(backupFile.absPath()))

        backupFile.createFromFile(self)
        backupFile.copyValuesFrom(self)

        return backupFile

    def rollBackToVersion(self, version):

        sMsg = "Rolling back to version: {}".format(version)
        logMsg(sMsg , warning=True)

        backupFile = self._weakBackupFile(version)
        if not backupFile.exists():
            raise RuntimeError("Backup file does NOT exists: \n\t> '{}'"
                               .format(backupFile.absPath()))

        sCurFilePath = self.absPath()
        _, bCopied = copyFile(backupFile.absPath(), sCurFilePath)
        if not bCopied:
            raise RuntimeError("File could not be copied: \n\t> '{}'"
                               .format(sCurFilePath))

        self.copyValuesFrom(backupFile)

        if version == 0:
            self._dbnode.delete()

    def createFromFile(self, srcFile):

        assert not self.exists(), "File already created: '{}'".format(self.absPath())
        assert srcFile.isFile(), "No such file: '{}'".format(srcFile.absPath())

        sCurDirPath = self.absDirPath()
        if not osp.exists(sCurDirPath):
            os.makedirs(sCurDirPath)

        sCurFilePath = self.absPath()
        _, bCopied = copyFile(srcFile.absPath(), sCurFilePath)
        if not bCopied:
            raise RuntimeError("File could not be copied: \n\t> '{}'"
                               .format(sCurFilePath))

        self.refresh()

        return True

    def getBackupDir(self):
        backupDir = self.library.getEntry(self.backupDirPath())
        #backupDir.loadChildDbNodes()
        return backupDir

    def backupDirPath(self):
        return pathJoin(self.absDirPath(), "_version")

    def setLocked(self, bLock, **kwargs):
        logMsg(log='all')

        sLockOwner = self.getLockOwner()
        sLoggedUser = self.library.project.getLoggedUser(force=True).loginName

        if sLockOwner:
            if sLockOwner == sLoggedUser:
                if bLock:
                    return True
            else:
                if kwargs.get("warn", True):
                    self.__warnAlreadyLocked(sLockOwner)
                    return False

        if self.setPrpty('locked', bLock):
            self.refresh()# must be done to get "lock" property updated
            return True

        return False

    def getLockOwner(self):

        if self.getPrpty("locked"):
            sLockOwner = self.getPrpty("lockOwner")
            if not sLockOwner:
                raise ValueError, 'Invalid value for lockOwner: "{0}"'.format(self)
            return sLockOwner

        return ""

    def nextVersionName(self):
        v = padded(self.latestBackupVersion() + 1)
        return pathSuffixed(self.name, '-v', v)

    def nameFromVersion(self, i):
        return pathSuffixed(self.name, '-v', padded(i))

    def suppress(self):
        parentDir = self.parentDir()
        if parentDir._qdir.remove(self.name):
            self.refresh(children=True, parent=parentDir)

    def _initialDbNodeData(self):
        data = DrcEntry._initialDbNodeData(self)
        data.update({"file":self.damasPath()})
        return data

    def _weakBackupFile(self, version):

        sBkupFilename = self.nameFromVersion(version)
        sBkupFilePath = pathJoin(self.backupDirPath(), sBkupFilename)

        return self.library._weakFile(sBkupFilePath)

    def __warnAlreadyLocked(self, sLockOwner, **kwargs):
        sMsg = u'{1}\n\n{2:^{0}}\n\n{3:^{0}}'.format(len(self.name) + 2, '"{0}"'.format(self.name), "locked by", (sLockOwner + " !").upper())
        confirmDialog(title="FILE LOCKED !"
                    , message=sMsg
                    , button=["OK"]
                    , defaultButton="OK"
                    , cancelButton="OK"
                    , dismissString="OK"
                    , icon=kwargs.pop("icon", "critical"))
        return
