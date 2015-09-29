
import os
import os.path as osp
import re
from datetime import datetime
import filecmp
from fnmatch import fnmatch

from PySide.QtCore import QDir

from pytd.gui.dialogs import confirmDialog

from pytd.util.logutils import logMsg
from pytd.util.qtutils import toQFileInfo
from pytd.util.fsutils import pathJoin, pathSuffixed, normCase
from pytd.util.fsutils import addEndSlash, pathNorm
from pytd.util.fsutils import copyFile
from pytd.util.fsutils import sha1HashFile
from pytd.util.qtutils import setWaitCursor
from pytd.util.strutils import padded
from pytd.util.fsutils import iterPaths

from pytd.gui.itemviews.utils import showPathInExplorer
from pytd.util.sysutils import timer#, getCaller
from pytd.util.external.send2trash import send2trash

from .drcproperties import DrcMetaObject
from .drcproperties import DrcEntryProperties, DrcFileProperties
from .utils import promptForComment
from .utils import versionFromName
from .locktypes import LockFile
from pytd.util.external import parse
from pytd.util.sysutils import toStr, hostApp#, getCaller
from pytd.util.sysutils import toTimestamp

#from davos.core.damtypes import DamEntity

_COPY_PRIV_SPACE_MSG = """
You have {0} version of '{1}':

    private file: {2}
    public  file: {3}
"""


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

        DrcMetaObject.loadData(self)

        #print self._dbnode, sAbsPath
        if (not self._dbnode) and self.isPublic():
            self._dbnode = self.getDbNode(fromDb=kwargs.get('dbNode', True))

            sDbPrptyNames = self.__class__.propertyPerAccessorDct["_dbnode"]
            DrcMetaObject.loadData(self, propertyNames=sDbPrptyNames)

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
            return True

        logMsg('Refreshing : {0}'.format(self), log='debug')

        bDbNode = kwargs.get("dbNode", True)
        bSimple = kwargs.get("simple", False)

        fileInfo = self._qfileinfo
        if bSimple:
            self.loadData(fileInfo, dbNode=bDbNode)
            return

        bChildren = kwargs.get("children", False)
        parent = kwargs.get("parent", None)

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

        for fileInfo in self._qdir.entryInfoList(nameFilters, **kwargs):
            entry = getEntry(fileInfo, dbNode=False)
            if entry:
                yield entry

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

    def envPath(self):
        return self.library.absToEnvPath(self.absPath())

    def dbPath(self):
        lib = self.library
        sLibPath = lib.absPath()
        sProjDmsPath = lib.project.getVar("project", "damas_root_path")
        sLibDmsPath = pathJoin(sProjDmsPath, lib.name)
        p = re.sub('^' + sLibPath, sLibDmsPath, self.absPath())
        return p

    def imagePath(self):
        return ''

    def getEntity(self, fail=False):
        p = self.absPath()
        damEntity = self.library.project.entityFromPath(p)
        if (not damEntity) and fail:
            raise RuntimeError("Could not get an entity from '{}'".format(p))

        return damEntity

    def getParam(self, sParam, default="NoEntry"):

        proj = self.library.project
        sAbsPath = self.absPath()
        data = proj.dataFromPath(sAbsPath)

        sSection = data.get("section")
        sRcName = data.get("resource")

        if not (sSection and sRcName):
            if default == "NoEntry":
                raise RuntimeError("{} is not a configured resource: '{}'"
                                   .format(self, sAbsPath))
            else:
                return default

        return proj.getRcParam(sSection, sRcName, sParam, default=default)

    ''
    #=======================================================================
    # Database related methods
    #=======================================================================

    def createDbNode(self, data=None, **kwargs):

        assert self.isPublic(), "File is NOT PUBLIC !"

        bCreated = False
        dbnode = None

        if kwargs.get("check", True):
            dbnode = self.getDbNode()

        if not dbnode:

            nodeData = {} if data is None else data.copy()
            nodeData.update({"file":self.dbPath()})

            #print "creating DbNode:", data
            dbnode = self.library._db.createNode(nodeData)
            if dbnode:
                bCreated = True
                self._cacheDbNode(dbnode)

        else:
            msg = u"{} already exists: '{}' !".format(dbnode, dbnode.file)
            raise RuntimeError(msg)

#            logMsg(u"DbNode already exists: '{}'".format(dbnode.file),
#                   warning=True)

        return dbnode, bCreated

    #@timer
    def getDbNode(self, fromDb=True):
        logMsg(log='all')

        assert self.isPublic(), "File is NOT PUBLIC !"

        cachedDbNodes = self.library._cachedDbNodes
        cacheKey = self.getDbCacheKey()

        dbnode = cachedDbNodes.get(cacheKey)
        if dbnode:
            logMsg(u"got from CACHE: '{}'".format(cacheKey), log='debug')
        elif fromDb:
            sQuery = u"file:/^{}$/i".format(self.dbPath())

#            print "finding DbNode:", sQuery
            dbnode = self.library._db.findOne(sQuery)
#            print "    - got:", dbnode

            if dbnode:
                logMsg(u"got from DB: '{}'".format(cacheKey), log='debug')
                self._cacheDbNode(dbnode, cachedDbNodes, cacheKey)

        if not dbnode:
            logMsg(u"no such dbnode: '{}'".format(cacheKey), log='debug')

        return dbnode

    def _cacheDbNode(self, dbnode, dbNodesCache=None, cacheKey=None, refresh=True):

        if dbNodesCache is None:
            dbNodesCache = self.library._cachedDbNodes

        if cacheKey is None:
            cacheKey = self.getDbCacheKey()

        logMsg(u"loading: '{}'".format(cacheKey), log='debug')
        dbNodesCache[cacheKey] = dbnode
        if refresh:
            self.refresh(simple=True)

    @timer
    def loadChildDbNodes(self):

        library = self.library
        cachedDbNodes = library._cachedDbNodes

        for dbnode in self.listChildDbNodes():

            sDbPath = dbnode.getField("file")

            cacheKey = normCase(sDbPath)
            cachedNode = cachedDbNodes.get(cacheKey)
            if cachedNode:
#                print "-----------------"
#                print "cachedNode", cacheKey
#                cachedNode.logData()
#                print "-----------------"
                cachedNode.refresh(dbnode._data)
            else:
                logMsg(u"loading: {}".format(cacheKey), log='debug')
                cachedDbNodes[cacheKey] = dbnode

    def listChildDbNodes(self, sQuery="", recursive=False, **kwargs):

        assert self.isPublic(), "File is NOT PUBLIC !"

        sFullQuery = self.childDbNodesQuery(sQuery, recursive=recursive)
        nodes = self.library._db.findNodes(sFullQuery, **kwargs)

#        print sFullQuery
#        for n in nodes:
#            n.logData()

        return nodes

    def childDbNodesQuery(self, sQuery="", recursive=False):

        if recursive:
            sBaseQuery = u"file:/^{}.+/i"
        else:
            sBaseQuery = u"file:/^{}[^/]+[/]*$/i"

        sDbPath = self.dbPath()

        sBaseQuery = sBaseQuery.format(sDbPath)#.replace(u"/", u"\/"))
        return " ".join((sBaseQuery, sQuery))

    def getDbCacheKey(self):
        return normCase(self.dbPath())

    def deleteDbNode(self):

        cachedDbNodes = self.library._cachedDbNodes

        cacheKey = self.getDbCacheKey()
        dbNode = cachedDbNodes.get(cacheKey)
        if not dbNode:
            return True

        if not dbNode.delete():
            return False

        print u"delete DbNode of", self
        del cachedDbNodes[cacheKey]
        self._dbnode = None

        self.refresh(simple=True)

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

    ''
    #=======================================================================
    # Sync rules methods
    #=======================================================================

    def setSyncRules(self, in_sRuleList, applyRules=True, **kwargs):

        drcEntry = None
        if not in_sRuleList:
            sRuleList, drcEntry = self.inheritedSyncRules()
        else:
            sRuleList = in_sRuleList

        syncData = self._evalSyncRules(sRuleList)
        print self, "applies", syncData, 'inherited from', drcEntry

        if applyRules:
            sPathIter, dbNodeDct = self.__beginApplySyncData()

        # set sync rules before actually applying sync data on each child nodes
        if not self._setPrpty("syncRules", in_sRuleList):
            return False

        if applyRules:
            self.__applySyncData(syncData, sPathIter, dbNodeDct)

        return True

    def __applySyncData(self, syncData, sPathIter, dbNodeDct):

        cachedDbNodes = self.library._cachedDbNodes
        proj = self.library.project

        prunedData = dict((k, v) for k, v in syncData.iteritems() if v is not None)

        print "Applying sync data:", syncData

        numCreated = 0
        toUpdateNodes = []
        #drcFileList = []
        for sPath in sPathIter:

            drcFile = proj.entryFromPath(sPath, dbNode=False)
            sDbPath = drcFile.dbPath()

            bCached = True
            dbNode = drcFile.getDbNode(fromDb=False)
            if not dbNode:
                dbNode = dbNodeDct.get(sDbPath)
                bCached = False

            if not dbNode:
                dbNode, _ = drcFile.createDbNode(data=prunedData, check=False)
                numCreated += 1
                print "create    ", sDbPath
            else:
                toUpdateNodes.append(dbNode)
                print "update    ", sDbPath

            if not bCached:
                drcFile._cacheDbNode(dbNode, cachedDbNodes, refresh=False)

            #drcFileList.append(drcFile)
            #print dbNode.dataRepr()

        proj._db.updateNodes(toUpdateNodes, syncData)

#        for drcFile in drcFileList:
#            drcFile.refresh(simple=True)

        print "- created: {} - updated: {} -".format(numCreated, len(toUpdateNodes))

    def __beginApplySyncData(self):

        sExcludePaths = []

        ruledNodes = self.listChildDbNodes("sync_rules:/.+/", recursive=True)
        if ruledNodes:

            for n in ruledNodes:
                ruledEntry = self.library.entryFromDbPath(n.file, dbNode=False)
                if not ruledEntry:
                    continue

                sExcludePaths.append(normCase(ruledEntry.absPath()))

        def ignorePaths(sDirPath, sNameList):

            ignoredNames = []
            for sName in sNameList:

                bFnMatched = False
                for sPat in ("*.db", ".*"):
                    if fnmatch(sName, sPat):
                        ignoredNames.append(sName)
                        bFnMatched = True
                        break

                if bFnMatched:
                    continue

                p = normCase(pathJoin(sDirPath, sName))
                if p in sExcludePaths:
                    ignoredNames.append(sName)

            return ignoredNames

        sPathIter = iterPaths(self.absPath(), ignoreFiles=ignorePaths,
                              ignoreDirs=ignorePaths, dirs=False)

        dbNodeDct = self.listChildDbNodes(recursive=True, asDict=True, keyField="file")

        return sPathIter, dbNodeDct

    def _evalSyncRules(self, in_sRuleList):

        sAllSites = set(self.library.project.listAllSites())

        sRuleList = in_sRuleList
        if len(sRuleList) == 1:
            sRule = sRuleList[0]
            if sRule == "all_sites":
                sRuleList = sAllSites
            elif sRule == "no_sync":
                sRuleList = []
            elif sRule not in sAllSites:
                raise ValueError("Invalid rule: '{}'".format(sRule))

        sSiteList = set(sRuleList)
        if sSiteList:
            sBadSites = sSiteList - sAllSites
            if sBadSites:
                raise ValueError("Unknown sites: {}".format(u",".join(sBadSites)))

        syncData = dict((s, 1 if s in sSiteList else None) for s in sAllSites)

        return syncData

    def inheritedSyncRules(self):

        library = self.library

        ruleNodeDct = library.listChildDbNodes("sync_rules:/.+/", recursive=True,
                                               asDict=True, keyField="file")
        libNode = library.getDbNode()
        ruleNodeDct[libNode.file] = libNode

        sRuleList = []
        drcEntry = None
        sDbPath = self.dbPath()
        #sLibDbPath = library.dbPath()
        while (sDbPath != '/'):

            sDbPath = addEndSlash(osp.dirname(pathNorm(sDbPath)))

            dbNode = ruleNodeDct.get(sDbPath)
            if dbNode:
                sRuleList = dbNode.getField("sync_rules")
                if sRuleList:
                    self._cacheDbNode(dbNode, refresh=False)
                    drcEntry = library.entryFromDbPath(sDbPath)
                    if drcEntry:
                        drcEntry.refresh(simple=True)
                        sRuleList = drcEntry.syncRules
                        break

            #print sDbPath, sRuleList, sLibDbPath
        return sRuleList, drcEntry

    def getSyncData(self):

        dbNode = self.getDbNode()
        sAllSites = self.library.project.listAllSites()
        return dbNode.getData(*sAllSites)

    ''
    #=======================================================================
    # Misc. methods
    #=======================================================================

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

    '@forceLog(log="debug")'
    def _writeAllValues(self, propertyNames=None):

        cls = self.__class__
        sPropertyList = tuple(cls._iterPropertyArg(propertyNames))

        logMsg("sPropertyList", sPropertyList, log='debug')

        sDbNodePrptySet = set(cls.filterPropertyNames(sPropertyList,
                                                       accessor="_dbnode",
                                                       ))

        logMsg("sDbNodePrptySet", sDbNodePrptySet, log='debug')
        sOtherPrptySet = set(sPropertyList) - sDbNodePrptySet

        logMsg("sOtherPrptySet", sOtherPrptySet, log='debug')
        DrcMetaObject._writeAllValues(self, propertyNames=sOtherPrptySet)

        data = self.dataToStore(sDbNodePrptySet)

        logMsg("Writing DbNode data:", data, self, log='debug')

        dbnode = self.getDbNode()
        if not dbnode:
            self.createDbNode(data, check=False)
        else:
            return dbnode.setData(data)


    def _remember(self):

        cacheKey = normCase(self.relPath())
        # print '"{}"'.format(self.relPath())
        _cachedEntries = self.library._cachedEntries

        if cacheKey in _cachedEntries:
            logMsg("Already useCache: {0}.".format(self), log="debug")
        else:
            logMsg("Caching: {0}.".format(self), log="debug")
            _cachedEntries[cacheKey] = self

    def _forget(self, parent=None, **kwargs):
        logMsg(self.__class__.__name__, log='all')

        bRecursive = kwargs.get("recursive", True)

        self.__forgetOne(parent)

        if bRecursive:
            for child in self.loadedChildren[:]:
                child._forget(parent, **kwargs)

    def __forgetOne(self, parent=None):

        cacheKey = normCase(self.relPath())
        _cachedEntries = self.library._cachedEntries

        if cacheKey not in _cachedEntries:
            logMsg("Already dropped: {0}.".format(self), log="debug")
        else:
            parentDir = parent if parent else self.parentDir()
            if parentDir and parentDir.loadedChildren:
                logMsg("Dropping {} from {}".format(self, parentDir), log="debug")
                parentDir.loadedChildren.remove(self)

            del self.loadedChildren[:]
            self.delModelRow()

            return _cachedEntries.pop(cacheKey)

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

    def dbPath(self):
        return addEndSlash(DrcEntry.dbPath(self))

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

    def sysOpen(self):

        p = self.absPath()
        _, sExt = osp.splitext(p)
        if sExt in (".ma", ".mb"):

            if hostApp() != "maya":
                raise RuntimeError("Can only be opened from Maya.")

            return self.mayaOpen()

        else:
            if os.name == "nt":
                os.system("explorer {}".format(osp.normpath(p)))
            else:
                raise NotImplementedError("Sorry, not implemented for your OS yet.")

    def mayaOpen(self):
        raise NotImplementedError("Sorry, not implemented yet.")

    def edit(self, openFile=False, existing=""):
        logMsg(log='all')

        self._assertEditable()

        privFile = None

        if not self.setLocked(True):
            return None

        try:
            privFile, _ = self.copyToPrivateSpace(suffix=self.makeEditSuffix(),
                                                  existing=existing)
        finally:
            if not privFile:
                self.restoreLockState()
                return None

        if openFile and (not hostApp()):
            privFile.showInExplorer()

        return privFile

    def choosePrivateFileToEdit(self):

        privDir = self.getPrivateDir()
        if not privDir:
            raise RuntimeError('Could not find the private directory !')

        sSuffix = self.makeEditSuffix(w='*')
        sNameFilter = pathSuffixed(self.name, sSuffix).replace(' ', '?')

        from PySide import QtGui
        sSrcFilePath, _ = QtGui.QFileDialog.getOpenFileName(None,
                                                            "Select a file to edit...",
                                                            privDir.absPath(),
                                                            sNameFilter
                                                            )
        if not sSrcFilePath:
            return None

        return privDir.library.getEntry(sSrcFilePath)

    def _assertEditable(self):

        self.refresh()

        if not self.getParam("editable", True):
            raise AssertionError("File is NOT EDITABLE !")

        if not self.isUpToDate():
            raise AssertionError("File is NOT UP-TO-DATE !")


    def isUpToDate(self):

        if not self.currentVersion:
            return True

        if not self.dbMtime:
            return True

        if self.dbMtime <= self.fsMtime:
            return True

        return False

    def iterEditedOutcomeFiles(self):

        assert self.isPrivate(), "File is NOT private !"

        v, w = self.getEditNums()

        for sRcName, pubFile in self.iterOutcomeFiles():
            privFile = pubFile.getEditFile(v, w, weak=True)
            yield sRcName, privFile

    def getEditNums(self):

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
        damEntity = pubFile.getEntity()

        if damEntity:
            sRcList = pubFile.getParam("outcomes", [])

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

        sVersion = self.versionSuffix(v)

        if w is not None:
            if isinstance(w, basestring):
                pass
            elif isinstance(w, int):
                w = padded(w)
            else:
                raise TypeError("argument 'w' must be of type <int> or <basestring>. Got {}."
                                .format(type(w)))
        else:
            w = padded(0)

        return "".join((sVersion, '.', w))

    def versionSuffix(self, v=None):
        if v is not None:
            if not isinstance(v, int):
                raise TypeError("argument 'v' must be of type <int>. Got {}."
                                .format(type(v)))
        else:
            v = self.currentVersion + 1

        return "".join(('-v', padded(v)))

    def copyToPrivateSpace(self, suffix="", existing="", **kwargs):

        exisintValues = ('', 'keep', 'abort', 'replace', 'overwrite', 'fail', 'choose')
        if existing not in exisintValues:
            raise ValueError("Bad value for 'existing' kwarg: '{}'. Must be {}"
                             .format(existing, exisintValues))

        privFile = self.getPrivateFile(suffix=suffix, weak=True)

        assert self.isFile(), "File does NOT exist !"
        assert versionFromName(self.name) is None, "File is already a version !"

        sPrivFilePath = privFile.absPath()
        sPubFilePath = self.absPath()
        # now let's make the private copy of that file
        if sPubFilePath == sPrivFilePath:
            raise ValueError('Source and destination files are identical: "{0}".'
                             .format(sPubFilePath))


        bDryRun = kwargs.get("dry_run", False)

        sPrivDirPath, sPrivFileName = osp.split(sPrivFilePath)
        if not osp.exists(sPrivDirPath):
            if not bDryRun:
                os.makedirs(sPrivDirPath)

        privLib = privFile.library

        bCopied = False
        bSameFiles = False

        if osp.exists(sPrivFilePath):

            if existing == "":

                bSameFiles = filecmp.cmp(sPubFilePath, sPrivFilePath, shallow=True)

                if not bSameFiles:

                    privFileTime = datetime.fromtimestamp(osp.getmtime(sPrivFilePath))
                    pubFileTime = datetime.fromtimestamp(osp.getmtime(sPubFilePath))

                    sState = "an OLDER" if privFileTime < pubFileTime else "a NEWER"

                    sMsg = _COPY_PRIV_SPACE_MSG.format(sState, sPrivFileName,
                                                       privFileTime.strftime("%A, %d-%m-%Y %H:%M"),
                                                       pubFileTime.strftime("%A, %d-%m-%Y %H:%M"),
                                                       )
                    sConfirm = confirmDialog(title='WARNING !'
                                            , message=sMsg.strip('\n')
                                            , button=['Keep', 'Overwrite', 'Cancel']
                                            , icon="warning")

                    if sConfirm == 'Cancel':
                        logMsg("Cancelled !", warning=True)
                        return None, bCopied

                    existing = sConfirm.lower()
                else:
                    existing = "keep"

            if existing == 'abort':
                return None, bCopied
            elif existing == 'keep':
                return privLib.getEntry(sPrivFilePath), bCopied
            elif existing == 'choose':
                if hostApp():
                    privFile = self.choosePrivateFileToEdit()
                else:
                    privFile = self.getLatestEditFile()
                return privFile, bCopied
            elif existing == 'fail':
                raise RuntimeError("Private file already exists: '{}'"
                                   .format(sPrivFilePath))
            else:#existing in ('replace', 'overwrite')
                pass

        if bSameFiles:
            logMsg('\nAlready copied "{0}" \n\t to: "{1}"'.format(sPubFilePath,
                                                                  sPrivFilePath))
        else:
            # logMsg('\nCoping "{0}" \n\t to: "{1}"'.format(sPubFilePath, sPrivFilePath))
            _, bCopied = copyFile(sPubFilePath, sPrivFilePath, **kwargs)

        return privLib.getEntry(sPrivFilePath), bCopied

    def getPrivateFile(self, suffix="", weak=False):

        assert self.isPublic(), "File is NOT PUBLIC !"

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

        #assert self.isFile(), "File does NOT exist !"
        assert self.isPublic(), "File is NOT PUBLIC !"

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

    def getLatestEditFile(self):

        privDir = self.getPrivateDir()
        if not privDir:
            return None

        sNameFilter = pathSuffixed(self.nextVersionName(), '*').replace(' ', '?')
        sEntryList = privDir._qdir.entryList((sNameFilter,),
                                               filters=QDir.Files,
                                               sort=(QDir.Name | QDir.Reversed))

        if not sEntryList:
            return None

        sFilePath = pathJoin(privDir.absPath(), sEntryList[0])
        return privDir.library.getEntry(sFilePath, dbNode=False)

    def ensureFilePublishable(self, privFile, version=None):

        assert privFile.isPrivate(), "File must live in a PRIVATE library !"
        assert not privFile.isReadOnly(), "File is READ-ONLY !"

        iSrcVers = versionFromName(privFile.name)
        iNxtVers = (self.currentVersion + 1) if version is None else version

        if iSrcVers < iNxtVers:
            raise AssertionError, "File version is OBSOLETE !"
        elif iSrcVers > iNxtVers:
            raise AssertionError, "File version is WHAT THE FUCK !"

        privFile.publishAsserted = True

    def isReadOnly(self):
        return "readonly" in self.name

    def publishEditedFile(self, editFile, **kwargs):

        if not editFile.publishAsserted:
            editFile.publishAsserted = False
            raise RuntimeError("DrcFile.ensureFilePublishable() has not been applied to {} !"
                               .format(editFile))

        sSrcFilePath = editFile.absPath()
        return self.publishVersion(sSrcFilePath, **kwargs)

    @setWaitCursor
    def publishVersion(self, sSrcFilePath, **kwargs):

        bAutoUnlock = kwargs.pop("autoUnlock", True)
        bSaveSha1Key = kwargs.pop("saveSha1Key", False)

        bDiffers, sSrcSha1Key = self.differsFrom(sSrcFilePath)
        if not bDiffers:
            logMsg("Skipping {0} increment: Files are identical.".format(self))
            return True

        sgVersion = None
        newVersFile = None

        # first, get all needed data from user or inputs
        try:
            sComment, iNextVers, bSgVersion, sgTaskInfo = self.beginPublish(**kwargs)
        except Exception, e:
            self._abortPublish(e, newVersFile, sgVersion)
            raise

        # create version file's DbNode and DrcFile.
        try:
            newVersFile = self._createVersionFile(sSrcFilePath, iNextVers, sComment,
                                                  saveSha1Key=bSaveSha1Key,
                                                  sha1Key=sSrcSha1Key)
        except Exception, e:
            self._abortPublish(e, newVersFile, sgVersion)
            raise

        # create shotgun version if possible else warn the user.
        if bSgVersion and sgTaskInfo:
            try:
                sgVersion = newVersFile.createSgVersion(sgTaskInfo, sComment)
                if not sgVersion:
                    raise RuntimeError("")
            except Exception, e:
                sMsg = "Failed to create Shotgun Version:\n\n" + toStr(e)
                sResult = confirmDialog(title='WARNING !',
                                        message=sMsg,
                                        button=["Continue", "Abort"],
                                        defaultButton="Continue",
                                        cancelButton="Abort",
                                        dismissString="Abort",
                                        icon="warning")
                if sResult == "Abort":
                    logMsg("Cancelled !", warning=True)
                    return self._abortPublish(e, newVersFile, sgVersion)

                sgVersion = None


        #iPrevMtime = osp.getmtime(sSrcFilePath)
        # copy source file as new version file
        try:
            iUtcStamp = toTimestamp(newVersFile.dbMtime)
            os.utime(sSrcFilePath, (iUtcStamp, iUtcStamp))
            copyFile(sSrcFilePath, newVersFile.absPath())
        except Exception, e:
            self._abortPublish(e, newVersFile, sgVersion)
            raise

        # copy metadata from version file to head file
        prevVersFile = self.getVersionFile(self.currentVersion, weak=False)
        try:
            self.copyValuesFrom(newVersFile)
        except Exception, e:
            self._abortPublish(e, newVersFile, sgVersion)
            raise

        # copy source file over head file
        try:
            copyFile(sSrcFilePath, self.absPath())
        except Exception, e:
            self.copyValuesFrom(prevVersFile)
            self._abortPublish(e, newVersFile, sgVersion)
            raise

        #os.utime(sSrcFilePath, (iPrevMtime, iPrevMtime))

        self.restoreLockState(autoUnlock=bAutoUnlock, refresh=False)
        self.refresh()

        return newVersFile, sgVersion

    def beginPublish(self, comment="", autoLock=False, version=None, sgTask=None,
                     checkLock=True):
        logMsg(log='all')

        if checkLock:
            self.ensureLocked(autoLock=autoLock)

        iNextVers = (self.currentVersion + 1)
        if version is not None:
            if version > self.currentVersion:
                iNextVers = version
            else:
                sMsg = ("'version' arg must be greater than current version: {}. Got {}."
                        .format(self.currentVersion, version))
                raise ValueError(sMsg)

        sgTaskInfo = None
        bSgVersion = self.getParam('create_sg_version', False)
        if bSgVersion:
            try:
                sgTaskInfo = self.__beginPublishSgVersion(sgTask)
            except Exception, e:
                sMsg = "Failed to get Shotgun Task:\n\n" + toStr(e)
                sResult = confirmDialog(title='WARNING !',
                                        message=sMsg,
                                        button=["Continue", "Abort"],
                                        defaultButton="Continue",
                                        cancelButton="Abort",
                                        dismissString="Abort",
                                        icon="warning")
                if sResult == "Abort":
                    raise

                bSgVersion = False

        sComment = comment
        if not sComment:
            sComment = promptForComment(text=self.getPrpty("comment"))

        # copy a first backup file if no version yet (usually a empty file)
        backupFile = None
        iCurVers = self.currentVersion
        if iCurVers == 0:
            backupFile = self.getVersionFile(0, weak=True)
            if not backupFile.exists():
                backupFile.createFromFile(self)

        return sComment, iNextVers, bSgVersion, sgTaskInfo

    def _abortPublish(self, err, versionFile=None, sgVersion=None):

        try:
            if versionFile:
                if versionFile._dbnode:
                    versionFile.deleteDbNode()

                if versionFile.exists():
                    os.remove(versionFile.absPath())

            if sgVersion:
                print "delete ", sgVersion
                self.library.project._shotgundb.sg.delete(sgVersion['type'],
                                                          sgVersion['id'])
        finally:
            self.restoreLockState()

            sMsg = "Publishing aborted: {0}".format(toStr(err))
            logMsg(sMsg , warning=True)

        return versionFile, sgVersion

    def __beginPublishSgVersion(self, sgTask):

        if not sgTask:
            damEntity = self.getEntity(fail=True)
            sTaskList = self.getParam("sg_tasks", default=[])
            if len(sTaskList) == 1:
                sgTaskInfo = damEntity._sgTaskFromCode(sTaskList[0], fail=True)
            else:
                sStepCode = self.getParam('sg_step', "")
                sgTaskInfo = damEntity.chooseSgTask(sStepCode, fromList=sTaskList)

        elif isinstance(sgTask, dict):
            sgTaskInfo = sgTask

        elif isinstance(sgTask, basestring):
            damEntity = self.getEntity(fail=True)
            sgTaskInfo = damEntity._sgTaskFromCode(sgTask, fail=True)
        else:
            raise TypeError("'sgTask' kwarg must be {} or {}. Got {}."
                            .format(dict, basestring, type(sgTask)))

        return sgTaskInfo

    def _createVersionFile(self, sSrcFilePath, iVersion, sComment,
                          saveSha1Key=False, sha1Key=""):

        versionFile = self.getVersionFile(iVersion, weak=True)
        sVersionPath = versionFile.absPath()
        if versionFile.exists():
            raise RuntimeError("Version file ALREADY exists:\n'{}'."
                               .format(sVersionPath))

        sLoggedUser = self.library.project.loggedUser().loginName

        if saveSha1Key:
            if not sha1Key:
                sNewSha1Key = sha1HashFile(sSrcFilePath)
            else:
                sNewSha1Key = sha1Key

            if sNewSha1Key:
                versionFile._setPrpty("checksum", sNewSha1Key, write=False)

        versionFile._setPrpty("comment", sComment, write=False)
        versionFile._setPrpty("sourceFile", sSrcFilePath, write=False)
        versionFile._setPrpty("author", sLoggedUser, write=False)
        versionFile._setPrpty("currentVersion", iVersion, write=False)

        sPropertyList = ("checksum", "comment", "sourceFile", "author",
                         "currentVersion",)

        data = versionFile.dataToStore(sPropertyList)
        syncData = self.getSyncData()
        data.update(syncData)

        logMsg("Creating version node: {}".format(data))
        dbNode, _ = versionFile.createDbNode(data)
        if not dbNode:
            raise RuntimeError("Could not create DbNode for {} !".format(versionFile))

        return versionFile

    def getVersionFile(self, iVersion, weak=False):

        sFilename = self.nameFromVersion(iVersion)
        sFilePath = pathJoin(self.backupDirPath(), sFilename)

        if weak:
            return self.library._weakFile(sFilePath)
        else:
            return self.library.getEntry(sFilePath)

    def createSgVersion(self, sgTaskInfo, comment=""):

        assert self.isPublic(), 'File is NOT PUBLIC !'
        assert versionFromName(self.name) is not None, "File is NOT a VERSION !"

        proj = self.library.project

        taskNameOrInfo = sgTaskInfo
        if "entity" not in sgTaskInfo:
            raise ValueError("'sgTaskInfo' arg must contain an 'entity' key !")

        entityNameOrInfo = sgTaskInfo.pop("entity")

        sVersionName = osp.splitext(self.name)[0]
        sComment = comment
        if not comment:
            sComment = self.comment

        sgVersion = proj.createSgVersion(sVersionName,
                                         entityNameOrInfo,
                                         taskNameOrInfo,
                                         sComment,
                                         self.envPath())
        return sgVersion

    def ensureLocked(self, autoLock=False):

        #print getCaller(), "ensureLocked"

        sLockOwner = self.getLockOwner()
        if not autoLock:
            if not sLockOwner:
                msg = u'"{0}" is not locked !'.format(self.name)
                raise RuntimeError(msg)

        if not self.setLocked(True, owner=sLockOwner):
            raise RuntimeError, "Could not lock the file !"

        return sLockOwner

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

            if (not bLock) and (not sLockOwner):
                return True

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

        if self._setPrpty('locked', bLock):
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

    def setSyncRules(self, sRuleList, **kwargs):
        return DrcEntry.setSyncRules(self, sRuleList, applyRules=False, **kwargs)

    def nextVersionName(self):
        v = self.currentVersion + 1
        return self.nameFromVersion(v)

    def nameFromVersion(self, v):
        return pathSuffixed(self.name, self.versionSuffix(v))

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
