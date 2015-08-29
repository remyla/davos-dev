
import os
import os.path as osp
import re
from datetime import datetime
import filecmp

from PySide.QtCore import QDir

from pytd.gui.dialogs import confirmDialog

from pytd.util.logutils import logMsg
from pytd.util.qtutils import toQFileInfo
from pytd.util.fsutils import pathJoin, pathSuffixed, normCase
from pytd.util.fsutils import pathRel, addEndSlash
from pytd.util.fsutils import copyFile
from pytd.util.fsutils import sha1HashFile
from pytd.util.qtutils import setWaitCursor
from pytd.util.strutils import padded
from pytd.gui.itemviews.utils import showPathInExplorer
from pytd.util.sysutils import timer#, getCaller
from pytd.util.external.send2trash import send2trash

from .drcproperties import DrcMetaObject
from .drcproperties import DrcEntryProperties, DrcFileProperties
from .utils import promptForComment
from .utils import versionFromName
from .locktypes import LockFile
from pytd.util.external import parse
from pytd.util.sysutils import isQtApp, toStr



class DrcEntry(DrcMetaObject):

    classUiPriority = 0

    propertiesDctItems = DrcEntryProperties
    propertiesDct = dict(propertiesDctItems)

    # defines which property will be displayed as a Tree in UI.
    primaryProperty = propertiesDctItems[0][0]


    def __init__(self, drcLib, absPathOrInfo=None, **kwargs):

        self.library = drcLib
        self._qfileinfo = None
        self._qdir = None
        self._dbnode = None
        self._lockobj = None

        self.loadedChildren = []
        self.childrenLoaded = False

        super(DrcEntry, self).__init__()

        fileInfo = toQFileInfo(absPathOrInfo)
        if fileInfo:

            if id(self) != id(drcLib):
                sAbsPath = fileInfo.filePath()
                if not drcLib.contains(fileInfo.absoluteFilePath()):
                    msg = u"Path is NOT part of {}: '{}'".format(drcLib, sAbsPath)
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

        #print self._dbnode, sAbsPath
        if (not self._dbnode) and self.isPublic():
            self._dbnode = self.getDbNode(fromDb=kwargs.get('dbNode', True))

        super(DrcEntry, self).loadData()

        sEntryName = self.name
        self.baseName, self.suffix = osp.splitext(sEntryName)
        self.label = sEntryName

        #print self, self._dbnode.logData() if self._dbnode else "Rien du tout"
        if not bRefreshing:
            self._remember()

        fileInfo.setCaching(False)

    def parentDir(self):
        return self.library.getEntry(self.relDirPath(), dbNode=False)

    #@timer
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
            if bDbNode and self._dbnode:
                self._dbnode.refresh()

            self.loadData(fileInfo, dbNode=bDbNode)

            self.updateModelRow()

            if bChildren and self.childrenLoaded:

                oldChildren = self.loadedChildren[:]

                for child in self.iterChildren():
                    if child not in oldChildren:
                        child.addModelRow(self)
                        self.loadedChildren.append(child)

                for child in oldChildren:
                    child.refresh(children=False, parent=self, dbNode=False)

    def isPublic(self):
        return self.library.space == "public"

    def isPrivate(self):
        return self.library.space == "private"

    def getChild(self, sChildName):
        return self.library.getEntry(pathJoin(self.absPath(), sChildName))

    def listChildren(self, *nameFilters, **kwargs):
        return tuple(self.iterChildren(*nameFilters, **kwargs))

    def loadChildren(self):

        self.childrenLoaded = True

        for child in self.iterChildren():
            child.addModelRow(self)
            self.loadedChildren.append(child)

    def iterChildren(self, *nameFilters, **kwargs):

        assert self.exists(), "No such directory: '{}'".format(self.absPath())

        if self.isPublic():
            self.loadChildDbNodes()

        getEntry = self.library.getEntry
        return (getEntry(info, dbNode=False) for info in self._qdir.entryInfoList(nameFilters, **kwargs))

    def hasChildren(self):
        return False

    ''
    #=======================================================================
    # Pathname related methods
    #=======================================================================

    def absDirPath(self):
        return self._qfileinfo.absolutePath()

    def relDirPath(self):
        return self.library.absToRelPath(self.absDirPath())

    def absPath(self):
        return self._qfileinfo.absoluteFilePath()

    def relPath(self):
        return self.library.absToRelPath(self.absPath())

    def absToRelPath(self, sAbsPath):
        return pathRel(sAbsPath, self.absPath())

    def relToAbsPath(self, sRelPath):
        return pathJoin(self.absPath(), sRelPath)

    def damasPath(self):
        lib = self.library
        sLibPath = lib.absPath()
        sProjDmsPath = lib.project.getVar("project", "damas_root_path")
        sLibDmsPath = pathJoin(sProjDmsPath, lib.name)
        p = re.sub('^' + sLibPath, sLibDmsPath, self.absPath())
        return normCase(p)

    def damasToRelPath(self, sDamasPath):
        p = sDamasPath
        bHasEndSlash = (p.endswith('/') or p.endswith('\\'))
        sRelPath = pathRel(sDamasPath, self.library.damasPath())
        return addEndSlash(sRelPath) if bHasEndSlash else sRelPath

    def imagePath(self):
        return ''

    def getEntity(self):
        return self.library.project.entityFromPath(self.absPath())

    def getParam(self, sParam, default="NoEntry"):

        proj = self.library.project
        sAbsPath = self.absPath()
        data = proj.dataFromPath(sAbsPath)
        sRcName = data.get("resource", "")
        if not sRcName:
            raise RuntimeError("{} is not a configured resource: '{}'"
                               .format(self, sAbsPath))

        sSection = data["section"]
        return proj.getRcParam(sSection, sRcName, sParam, default=default)

    ''
    #=======================================================================
    # Database related methods
    #=======================================================================

    #@timer
    def getDbNode(self, create=False, fromDb=True):
        logMsg(log='all')

        assert self.isPublic(), "File is NOT public !"

        _cachedDbNodes = self.library._cachedDbNodes

        cacheKey = self.getDbCacheKey()
        dbnode = _cachedDbNodes.get(cacheKey)
        if dbnode:
            logMsg(u"got from CACHE: '{}'".format(cacheKey), log='debug')
            return dbnode
        elif fromDb:
            dbnode = self.findDbNode(useCache=False)
            if dbnode:
                logMsg(u"got from DB: '{}'".format(cacheKey), log='debug')

        if (not dbnode) and create:
            dbnode = self.createDbNode(useCache=False)
            logMsg(u"just created: '{}'".format(cacheKey), log='debug')

        if dbnode:
            logMsg(u"loading: '{}'".format(cacheKey), log='debug')
            _cachedDbNodes[cacheKey] = dbnode
        else:
            logMsg(u"not such dbnode: '{}'".format(cacheKey), log='debug')

        return dbnode

    def findDbNode(self, useCache=True):
        logMsg(log='all')

        assert self.isPublic(), "File is NOT public !"

        if useCache:
            _cachedDbNodes = self.library._cachedDbNodes
            cacheKey = self.getDbCacheKey()
            if cacheKey in _cachedDbNodes:
                return _cachedDbNodes[cacheKey]

        sQuery = u"file:{}".format(self.damasPath())
#        print "finding DbNode:", sQuery
        dbnode = self.library._db.findOne(sQuery)
#        print "    - got:", dbnode

        if useCache and dbnode:
            logMsg(u"loading DbNode: {}".format(cacheKey), log='debug')
            _cachedDbNodes[cacheKey] = dbnode

        return dbnode

    def createDbNode(self, useCache=True):

        assert self.isPublic(), "File is NOT public !"

        if useCache:
            _cachedDbNodes = self.library._cachedDbNodes
            cacheKey = self.getDbCacheKey()
            if cacheKey in _cachedDbNodes:
                return _cachedDbNodes[cacheKey]

        dbnode = self.findDbNode(useCache=False)
        if not dbnode:
            data = {"file":self.damasPath()}
            dbnode = self.library._db.createNode(data)
        else:
            print u"DbNode already created: '{}'".format(dbnode.file)

        if useCache and dbnode:
            logMsg(u"loading DbNode: {}".format(cacheKey), log='debug')
            _cachedDbNodes[cacheKey] = dbnode

        return dbnode

    @timer
    def loadChildDbNodes(self):

        _cachedDbNodes = self.library._cachedDbNodes

        for dbnode in self.listChildDbNodes():

            sDamasPath = dbnode.getField("file")

            cacheKey = self.damasToRelPath(sDamasPath)
            cachedNode = _cachedDbNodes.get(cacheKey)
            if cachedNode:
#                print "-----------------"
#                print "cachedNode", cacheKey
#                cachedNode.logData()
#                print "-----------------"
                cachedNode.refresh(dbnode._data)
            else:
                logMsg(u"loading: {}".format(cacheKey), log='debug')
                _cachedDbNodes[cacheKey] = dbnode

    def listChildDbNodes(self, sQuery="", **kwargs):

        assert self.isPublic(), "File is NOT public !"

        if kwargs.pop('recursive', False):
            sBaseQuery = u"file:/^{}/"
        else:
            sBaseQuery = u"file:/^{}[^/]*$/"

        sBaseQuery = sBaseQuery.format(self.damasPath())
        sFullQuery = " ".join((sBaseQuery, sQuery))

        return self.library._db.findNodes(sFullQuery, **kwargs)

    def getDbCacheKey(self):
        return normCase(self.relPath())

    ''
    #=======================================================================
    # Model/View related methods
    #=======================================================================

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

    def iconSource(self):
        return self._qfileinfo

    def sendToTrash(self):

        assert not self.isPublic(), (u"Cannot delete a public file: \n\n    '{}'"
                                  .format(self.relPath()))

        send2trash(self.absPath())
        self.refresh(children=True)

    def showInExplorer(self, isFile=False):

        sPath = self.absPath()
        assert self.isPrivate(), "File is NOT private: '{}'".format(sPath)

        return showPathInExplorer(sPath, isFile)

    def _writeAllValues(self, propertyNames=None):

        sPropertyList = tuple(self.__class__._iterPropertyArg(propertyNames))

        logMsg("sPropertyList", sPropertyList, log='debug')

        sDbNodePrptySet = set(self.filterPropertyNames(sPropertyList,
                                                       accessor="_dbnode",
                                                       stored=True))

        sOtherPrptySet = set(sPropertyList) - sDbNodePrptySet

        logMsg("sOtherPrptySet", sOtherPrptySet, log='debug')
        DrcMetaObject._writeAllValues(self, propertyNames=sOtherPrptySet)

        logMsg("sDbNodePrptySet", sDbNodePrptySet, log='debug')
        values = self.getStoredValues(sDbNodePrptySet)

        logMsg("Writing DbNode data:", values, self, log='debug')
        self.getDbNode(create=True).setData(values)

    def _remember(self):

        key = self.relPath()
        # print '"{}"'.format(self.relPath())
        _cachedEntries = self.library._cachedEntries

        if key in _cachedEntries:
            logMsg("Already useCache: {0}.".format(self), log="debug")
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

    def getHomonym(self, sSpace, weak=False, create=False):

        curLib = self.library
        homoLib = curLib.getHomonym(sSpace)

        sHomoLibPath = homoLib.absPath()
        sHomoPath = re.sub("^" + curLib.absPath(), sHomoLibPath, self.absPath())

        if weak:
            return homoLib._weakDir(sHomoPath)

        if not osp.exists(sHomoPath) and create:
            os.makedirs(sHomoPath)

        return homoLib.getEntry(sHomoPath)

    def damasPath(self):
        return addEndSlash(DrcEntry.damasPath(self))

    def imagePath(self):

        sRootPath, sDirName = osp.split(self.absPath())
        sFileName = sDirName + "_preview.jpg"
        return pathJoin(sRootPath, sDirName, sFileName)

    def getDbCacheKey(self):
        return addEndSlash(DrcEntry.getDbCacheKey(self))

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

        self.publishAsserted = False
        self.__previousLock = "NoLockToRestore"

        super(DrcFile, self).__init__(drcLibrary, absPathOrInfo, **kwargs)

    def loadData(self, fileInfo, **kwargs):

        bFileLock = False
        if bFileLock:
            sLogin = self.library.project.loggedUser().loginName
            self._lockobj = LockFile(fileInfo.absoluteFilePath(), sLogin)

        DrcEntry.loadData(self, fileInfo, **kwargs)

        dbNode = self._dbnode
        if not (dbNode and dbNode.hasField("version")):
            self.updateCurrentVersion()

    def updateCurrentVersion(self):

        v = versionFromName(self.name)
        if v is None:
            v = self.latestBackupVersion()
        self.currentVersion = v

    def edit(self):
        logMsg(log='all')

        if not self.setLocked(True):
            return

        try:
            privFile = self.copyToPrivateSpace(suffix=self.makeEditSuffix())
        except:
            self.restoreLockState()
            raise

        if not privFile:
            self.restoreLockState()

        return privFile

    def isEditable(self):
        return self.getParam("editable", True)

    def iterEditedOutcomeFiles(self):

        v, w = self.getEditNums()

        for sRcName, pubFile in self.iterOutcomeFiles():
            privFile = pubFile.getEditFile(v, w, weak=True)
            yield sRcName, privFile

    def getEditNums(self):

        assert self.isPrivate(), "File is NOT private !"

        editSuffixFmt = "-v{v:03d}.{w:03d}"
        editNameFmt = "{root}" + editSuffixFmt + "{ext}"

        parseRes = parse.parse(editNameFmt, self.name)
        if not parseRes:
            return None, None

        v = parseRes.named.get("v", None)
        w = parseRes.named.get("w", None)

        return v, w

    def iterOutcomeFiles(self, weak=False):

        pubFile = self if self.isPublic() else self.getPublicFile(fail=True)

        pubLib = pubFile.library
        sRcList = pubFile.getParam("outcomes", [])
        damEntity = pubFile.getEntity()

        for sRcName in sRcList:
            sFilePath = damEntity.getPath("public", sRcName)
            if weak:
                drcFile = pubLib._weakFile(sFilePath)
            else:
                drcFile = pubLib.getEntry(sFilePath)

            if drcFile:
                yield sRcName, drcFile

    def getEditFile(self, v=None, w=None, weak=False):

        sSuffix = self.makeEditSuffix(v, w)
        return self.getPrivateFile(suffix=sSuffix, weak=weak)

    def makeEditSuffix(self, v=None, w=None):

        if v:
            if not isinstance(v, int):
                raise TypeError("argument 'v' must be of type <int>. Got {}."
                                .format(type(v)))
        else:
            v = self.currentVersion + 1

        if w:
            if not isinstance(w, int):
                raise TypeError("argument 'w' must be of type <int>. Got {}."
                                .format(type(w)))
        else:
            w = 0

        return "".join(('-v', padded(v), '.', padded(w)))

    def copyToPrivateSpace(self, suffix="", force=False, **kwargs):

        privFile = self.getPrivateFile(suffix=suffix, weak=True)

        assert self.isFile(), "File does NOT exist !"
        assert versionFromName(self.name) is None, "File is already a version !"

        sPrivFilePath = privFile.absPath()
        sPubFilePath = self.absPath()
        # now let's make the private copy of that file
        if sPubFilePath == sPrivFilePath:
            raise ValueError('Source and destination files are identical: "{0}".'
                             .format(sPubFilePath))

        bForce = force
        bDryRun = kwargs.get("dry_run", False)

        sPrivDirPath, sPrivFileName = osp.split(sPrivFilePath)
        if not osp.exists(sPrivDirPath):
            if not bDryRun:
                os.makedirs(sPrivDirPath)

        privLib = privFile.library

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
""".format(sState, sPrivFileName,
           privFileTime.strftime("%A, %d-%m-%Y %H:%M"),
           pubFileTime.strftime("%A, %d-%m-%Y %H:%M"),
           )
                sConfirm = confirmDialog(title='WARNING !'
                                        , message=sMsg.strip('\n')
                                        , button=['Keep', 'Overwrite', 'Cancel']
                                        , icon="warning")

                if sConfirm == 'Cancel':
                    logMsg("Cancelled !", warning=True)
                    return None
                elif sConfirm == 'Keep':
                    return privLib.getEntry(sPrivFilePath)

        if bSameFiles:
            logMsg('\nAlready copied "{0}" \n\t to: "{1}"'.format(sPubFilePath,
                                                                  sPrivFilePath))
        else:
            # logMsg('\nCoping "{0}" \n\t to: "{1}"'.format(sPubFilePath, sPrivFilePath))
            copyFile(sPubFilePath, sPrivFilePath, **kwargs)

        return privLib.getEntry(sPrivFilePath)

    def getPrivateFile(self, suffix="", weak=False):

        assert self.isPublic(), "File is NOT public !"

        pubDir = self.parentDir()
        privDir = pubDir.getHomonym('private', weak=weak)
        if not privDir:
            return None

        sPrivDirPath = privDir.absPath()
        sPrivFileName = self.fileName()
        sPrivFilePath = pathJoin(sPrivDirPath, sPrivFileName)

        if suffix:
            sPrivFilePath = pathSuffixed(sPrivFilePath, suffix)

        if weak:
            return privDir.library._weakFile(sPrivFilePath)
        else:
            return privDir.library.getEntry(sPrivFilePath)

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

    def getPublicFile(self, fail=False):

        #assert self.isFile(), "File does NOT exist !"
        assert self.isPrivate(), "File must live in a PRIVATE library !"

        privDir = self.parentDir()
        pubDir = privDir.getHomonym('public')

        sPrivFilename , sExt = osp.splitext(self.name)

        sPubDirPath = pubDir.absPath()
        sPubFilename = sPrivFilename.split('-v')[0] + sExt
        sPubFilePath = pathJoin(sPubDirPath, sPubFilename)

        pubFile = pubDir.library.getEntry(sPubFilePath, dbNode=False)

        if not pubFile and fail:
            raise RuntimeError("Could not get public version of '{}'"
                               .format(self.relPath()))

        return pubFile

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
        return self.library.getEntry(sFilePath, dbNode=False)

    def ensureFilePublishable(self, privFile, version=None):

        assert privFile.isPrivate(), "File must live in a PRIVATE library !"

        iSrcVers = versionFromName(privFile.name)
        iNxtVers = (self.currentVersion + 1) if version is None else version

        if iSrcVers < iNxtVers:
            raise AssertionError, "File version is OBSOLETE !"
        elif iSrcVers > iNxtVers:
            raise AssertionError, "File version is WHAT THE FUCK !"

        privFile.publishAsserted = True

    @setWaitCursor
    def incrementVersion(self, srcFile, **kwargs):

        if not srcFile.publishAsserted:
            srcFile.publishAsserted = False
            raise RuntimeError("DrcFile.ensureFilePublishable() has not been applied to {} !"
                               .format(srcFile))

        bAutoUnlock = kwargs.pop("autoUnlock", True)
        bSaveSha1Key = kwargs.pop("saveSha1Key", False)

        sSrcFilePath = srcFile.absPath()

        bDiffers, sSrcSha1Key = self.differsFrom(sSrcFilePath)
        if not bDiffers:
            logMsg("Skipping {0} increment: Files are identical.".format(self))
            return True

        backupFile = None
        sgVersionInfo = None

        try:
            sComment, iNextVers, _, sgVersionInfo = self.beginPublish(**kwargs)
        except RuntimeError, e:
            self.abortPublish(e, backupFile, bAutoUnlock)
            raise

        try:
            copyFile(sSrcFilePath, self.absPath())
        except Exception, e:
            self.abortPublish(e, backupFile, sgVersionInfo, bAutoUnlock)
            raise

        #save the current version that will be incremented in endPublish
        #in case we need to do a rollback caused by an Exception
        iSavedVers = self.currentVersion
        try:
            self.endPublish(sSrcFilePath, sComment,
                            saveSha1Key=bSaveSha1Key,
                            sha1Key=sSrcSha1Key,
                            autoUnlock=bAutoUnlock,
                            version=iNextVers)
        except Exception, e:
            self.abortPublish(e, backupFile, sgVersionInfo, bAutoUnlock)
            self.rollBackToVersion(iSavedVers)
            raise

        return True

    def beginPublish(self, comment="", autoLock=False, version=None):
        logMsg(log='all')

        sComment = comment

        self.ensureLocked(autoLock=autoLock)

        iNextVers = (self.currentVersion + 1)
        if version is not None:
            if version > self.currentVersion:
                iNextVers = version
            else:
                sMsg = ("Argument 'version' must be greater than current version: {}. Got {}."
                        .format(self.currentVersion, version))
                raise ValueError(sMsg)

        if not sComment:
            sComment = promptForComment(text=self.getPrpty("comment"))

        backupFile = None
        iCurVers = self.currentVersion
        if iCurVers == 0:
            backupFile = self._weakBackupFile(0)
            if not backupFile.exists():
                backupFile.createFromFile(self)

        sgVersionInfo = None
        bSgVersion = self.getParam('create_sg_version', False)
        if bSgVersion:
            sVersionName = osp.splitext(self.nameFromVersion(iNextVers))[0]
            sgVersionInfo = self.createSgVersion(sVersionName, sComment)
            if not sgVersionInfo:
                raise RuntimeError("Could not create shotgun version !")

        return sComment, iNextVers, backupFile, sgVersionInfo


    def createSgVersion(self, sVersionName, sComment):

        damEntity = self.getEntity()
        sTaskList = self.getParam("sg_tasks")
        if len(sTaskList) == 1:
            sTaskName = sTaskList[0]
        else:
            sMsg = "What was your task ?"
            if isQtApp():
                from PySide import QtGui
                sTaskName, bOk = QtGui.QInputDialog.getItem(None, "Make your choice !",
                                                            sMsg,
                                                            sTaskList,
                                                            current=0,
                                                            editable=False,
                                                            )

                if not bOk:
                    raise RuntimeError("No task selected !")
            else:
                sChoiceList = list(sTaskList) + ["Cancel"]
                sMsg += "({})".format("/".join(sChoiceList))
                sChoice = ""
                while sChoice not in sChoiceList:
                    sChoice = raw_input(sMsg)

                if sChoice == "Cancel":
                    raise RuntimeError("No task selected !")

                sTaskName = sChoice

        return damEntity.createSgVersion(sVersionName, sTaskName, sComment)

    def ensureLocked(self, autoLock=False):

        sLockOwner = self.getLockOwner()
        if not autoLock:
            if not sLockOwner:
                msg = u'"{0}" is not locked !'.format(self.name)
                raise RuntimeError(msg)

        if not self.setLocked(True, owner=sLockOwner):
            raise RuntimeError, "Could not lock the file !"

    def endPublish(self, sSrcFilePath, sComment, autoUnlock=True,
                   saveSha1Key=False, sha1Key="", version=None):

        self.setPrpty("comment", sComment, write=False)

        if saveSha1Key:
            if not sha1Key:
                sNewSha1Key = sha1HashFile(sSrcFilePath)
            else:
                sNewSha1Key = sha1Key

            self.setPrpty("checksum", sNewSha1Key, write=False)

        self.setPrpty("sourceFile", sSrcFilePath, write=False)

        sLoggedUser = self.library.project.loggedUser().loginName
        self.setPrpty("author", sLoggedUser, write=False)

        iNxtVers = (self.currentVersion + 1) if version is None else version
        self.setPrpty("currentVersion", iNxtVers, write=False)

        self.writeAllValues()

        backupFile = self.createBackupFile(iNxtVers)
        if not backupFile:
            raise RuntimeError, "Could not create backup file !"

        self.restoreLockState(autoUnlock, refresh=False)
        self.refresh()

    def abortPublish(self, err, backupFile=None, sgVersionInfo=None, autoUnlock=False):

        try:
            if backupFile:

                sBkupFilePath = backupFile.absPath()
                sCurFilePath = self.absPath()
                bSameFiles = filecmp.cmp(sCurFilePath, sBkupFilePath, shallow=True)
                if not bSameFiles:
                    copyFile(sBkupFilePath, sCurFilePath)

                backupFile.suppress()

            if sgVersionInfo:
                print "delete ", sgVersionInfo
                self.library.project._shotgundb.sg.delete(sgVersionInfo['type'],
                                                          sgVersionInfo['id'])

        finally:
            self.restoreLockState(autoUnlock)

            sMsg = "Publishing aborted: {0}".format(toStr(err))
            logMsg(sMsg , warning=True)

        return True

    def restoreLockState(self, autoUnlock=False, refresh=True):
        logMsg(log='all')

        try:
            sPrevLock = self.__previousLock
            sLoggedUser = self.library.project.loggedUser().loginName

            bRestore = (sPrevLock in ("", sLoggedUser))

            if autoUnlock:
                bRestore = bRestore or (sPrevLock == "NoLockToRestore")
                bLock = False
                print "auto-unlocking"
            else:
                bRestore = bRestore and (sPrevLock != "NoLockToRestore")
                bLock = True if sPrevLock else False
                print "restoring lock to", bLock

            if bRestore:
                self.setLocked(bLock, owner=sLoggedUser, refresh=False)
                if refresh:
                    self.refresh()

        finally:
            self.__previousLock = "NoLockToRestore"

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

        prevBackupFile = self._weakBackupFile(version)
        if not prevBackupFile.exists():
            raise RuntimeError("Rollback file does NOT exists: \n\t> '{}'"
                               .format(prevBackupFile.absPath()))

        sCurFilePath = self.absPath()
        _, bCopied = copyFile(prevBackupFile.absPath(), sCurFilePath)
        if not bCopied:
            raise RuntimeError("Rollback File could not be copied: \n\t> '{}'"
                               .format(sCurFilePath))

        curBackupFile = self._weakBackupFile(self.currentVersion)
        if not curBackupFile.exists():
            raise RuntimeError("Current backup file does NOT exists: \n\t> '{}'"
                               .format(curBackupFile.absPath()))

        try:
            self.copyValuesFrom(prevBackupFile)
        finally:

            if curBackupFile._dbnode:
                print "delete dbnode of ", self
                curBackupFile._dbnode.delete()

            sOldPath = curBackupFile.absPath()
            sNewPath = pathSuffixed(sOldPath, "-canceled")
            os.rename(sOldPath, sNewPath)

            curBackupFile.refresh(dbNode=False)

        if version == 0 and self._dbnode:
            self._dbnode.delete()

        return True

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
        backupDir = self.library.getEntry(self.backupDirPath(), dbNode=False)
        return backupDir

    def backupDirPath(self):
        return pathJoin(self.absDirPath(), "_version")

    def setLocked(self, bLock, **kwargs):
        logMsg(log='all')

        self.__previousLock = "NoLockToRestore"

        if not kwargs.get("force", False):

            sLockOwner = kwargs.get("owner", "NoEntry")
            if sLockOwner == "NoEntry":
                sLockOwner = self.getLockOwner()

            sLoggedUser = self.library.project.loggedUser(force=True).loginName

            if sLockOwner:
                if sLockOwner == sLoggedUser:
                    if bLock:
                        return True
                else:
                    if kwargs.get("warn", True):
                        self.__warnAlreadyLocked(sLockOwner)
                    return False

            #save the lock state so we can restore it later with restoreLockState()
            self.__previousLock = sLockOwner

        if self.setPrpty('locked', bLock):
            if kwargs.get("refresh", True):
                self.refresh()
            return True

        return False

    def getLockOwner(self):

        self.refresh()

        if self.getPrpty("locked"):
            sLockOwner = self.getPrpty("lockOwner")
            if not sLockOwner:
                raise ValueError('Invalid value for lockOwner: "{0}"'.format(self))
            return sLockOwner

        return ""

    def nextVersionName(self):
        v = self.currentVersion + 1
        return self.nameFromVersion(v)

    def nameFromVersion(self, v):
        return pathSuffixed(self.name, '-v', padded(v))

    def imagePath(self):
        sRoot, sExt = osp.splitext(self.absPath())
        return sRoot + sExt.replace('.', '_') + "_preview.jpg"

    def suppress(self):
        parentDir = self.parentDir()
        if parentDir._qdir.remove(self.name):
            parentDir.refresh(children=True)

    def showInExplorer(self):
        return DrcEntry.showInExplorer(self, isFile=True)

    def absToRelPath(self, sAbsPath):
        raise NotImplementedError('Not applicable to a File')

    def relToAbsPath(self, sRelPath):
        raise NotImplementedError('Not applicable to a File')

    def _weakBackupFile(self, version):

        sBkupFilename = self.nameFromVersion(version)
        sBkupFilePath = pathJoin(self.backupDirPath(), sBkupFilename)

        return self.library._weakFile(sBkupFilePath)

    def __warnAlreadyLocked(self, sLockOwner, **kwargs):
        sMsg = u'{1}\n\n{2:^{0}}\n\n{3:^{0}}'.format(len(self.name) + 2,
                                                     '"{0}"'.format(self.name),
                                                     "locked by",
                                                     (sLockOwner + " !").upper())
        confirmDialog(title="FILE LOCKED !"
                    , message=sMsg
                    , button=["OK"]
                    , defaultButton="OK"
                    , cancelButton="OK"
                    , dismissString="OK"
                    , icon=kwargs.pop("icon", "critical"))
        return
