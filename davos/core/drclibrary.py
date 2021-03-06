
import os
import os.path as osp
import re

from PySide.QtCore import QFileInfo

from pytd.util.logutils import logMsg

from pytd.util.sysutils import listClassesFromModule, getCaller
from pytd.util.qtutils import toQFileInfo
from pytd.util.fsutils import pathNorm, normCase, pathSplitDirs, pathJoin
from pytd.util.fsutils import pathRelativeTo
from pytd.util import sysutils

from . import drctypes
from .drctypes import DrcEntry, DrcDir, DrcFile
#from .dbtypes import DrcDb
from fnmatch import fnmatch


class DrcLibrary(DrcDir):

    classLabel = "library"
    classReprAttr = "fullName"
    classUiPriority = 0

    classFile = DrcFile
    classDir = DrcDir

    def __init__(self, sLibName, sLibPath, sSpace="", project=None, **kwargs):

        self._cachedEntries = {}
        self._cachedDbNodes = {}

        self.sectionName = sLibName
        self.fullName = DrcLibrary.makeFullName(sSpace, sLibName)
        self.space = sSpace
        self.project = project

        super(DrcLibrary, self).__init__(self, sLibPath, **kwargs)

    @property
    def _itemmodel(self):
        proj = self.project
        return proj._itemmodel if proj else None

    @property
    def _db(self):
        proj = self.project
        return proj._db if proj else None

    def loadData(self, fileInfo, **kwargs):
        logMsg(log="all")

        super(DrcLibrary, self).loadData(fileInfo, **kwargs)

        self.label = self.fullName if sysutils.inDevMode() else self.name

    def addModelRow(self):

        model = self._itemmodel
        if model:
            model.loadRowItems(self, model)

    def displayViewItems(self):

        bDevMode = sysutils.inDevMode()
        if (not bDevMode) and (self.space == "private"):
            return False

        return True

    @staticmethod
    def makeFullName(*names):
        return "|".join(names)

    @staticmethod
    def listUiClasses():
        return sorted((cls for (_, cls) in listClassesFromModule(drctypes.__name__)
                            if hasattr(cls, "classUiPriority")), key=lambda c: c.classUiPriority)

    def entryFromDbPath(self, sDbPath, **kwargs):
        bWeak = kwargs.pop("weak", False)

        sAbsPath = self.dbToAbsPath(sDbPath)
        if bWeak:
            return self._weakFile(sAbsPath, **kwargs)
        else:
            return self.getEntry(sAbsPath, **kwargs)

    def getEntry(self, pathOrInfo, weak=False, drcType=None, dbNode=True):
        logMsg(log="all")
        """
        weak means that we do not check if the path exists.  
        """

        fileInfo = None
        sRelPath = ""

        if isinstance(pathOrInfo, QFileInfo):
            sAbsPath = pathOrInfo.absoluteFilePath()
            fileInfo = pathOrInfo
        elif isinstance(pathOrInfo, basestring):
            sAbsPath = pathNorm(pathOrInfo)
            if not osp.isabs(sAbsPath):
                sRelPath = sAbsPath
                sAbsPath = self.relToAbsPath(sRelPath)
        else:
            raise TypeError("argument 'pathOrInfo' must be of type <QFileInfo> \
                            or <basestring>. Got {}.".format(type(pathOrInfo)))

        # entries are cached using their relative path the the library they belong to.
        if not sRelPath:
            sRelPath = self.absToRelPath(sAbsPath) if osp.isabs(sAbsPath) else sAbsPath

        # try to get an already loaded entry...
        drcEntry = self._cachedEntries.get(normCase(sRelPath))
        if drcEntry:
            drcEntry.loadData(drcEntry._qfileinfo, dbNode=dbNode)
            if weak:
                return drcEntry
            else:
                return drcEntry if drcEntry.exists() else None

        if not weak:
            sIgnorePatterns = ("*.db", ".*")
            sName = osp.basename(sAbsPath)
            for sPattern in sIgnorePatterns:
                if fnmatch(sName, sPattern):
                    return None

        if not fileInfo:
            fileInfo = toQFileInfo(sAbsPath)

        cls = self.__class__
        # no cached entry found so let's instance a new one
        if weak:
            if drcType:
                rcCls = drcType
            else:
                rcCls = cls.classDir if sAbsPath.endswith('/') else cls.classFile
        else:
            if fileInfo.isDir():
                rcCls = cls.classDir
            elif fileInfo.isFile():
                rcCls = cls.classFile
            else:
                return None

        entry = rcCls(self, fileInfo, dbNode=dbNode)

        return entry

    def contains(self, sAbsPath):

        sLibPath = normCase(self.absPath())
        sPathDirs = pathSplitDirs(normCase(sAbsPath))

        numDirs = len(pathSplitDirs(sLibPath))
        sAlignedPath = pathJoin(*sPathDirs[:numDirs])

        return sAlignedPath == sLibPath

    def absToRelPath(self, sAbsPath):
        return pathRelativeTo(sAbsPath, self.absPath())

    def relToAbsPath(self, sRelPath):
        return pathJoin(self.absPath(), sRelPath)

    def absToEnvPath(self, sAbsPath, envVar="NoEntry"):

        if envVar == "NoEntry":
            sEnvVars = self.getVar(self.space + "_path_envars", default=None)
            if not sEnvVars:
                raise RuntimeError("No Env. variables configured for {}", self)
            sEnvVar = sEnvVars[0]
        else:
            sEnvVar = envVar

        if sEnvVar not in os.environ:
            raise EnvironmentError("No such env. variable: '{}'".format(sEnvVar))

        return re.sub('^' + self.absPath(), "$" + sEnvVar, sAbsPath)

    def dbToAbsPath(self, sDbPath):

        sDbPath = pathNorm(sDbPath)

        sLibPath = self.absPath()
        sLibDmsPath = pathNorm(self.dbPath())
        #print '^' + sLibDmsPath, sLibPath, sDbPath
        sAbsPath = re.sub('^' + sLibDmsPath, sLibPath, sDbPath)

        if sDbPath == sAbsPath:
            raise ValueError("{} could not convert damas path to absolute: '{}'"
                               .format(self, sDbPath))

        return sAbsPath

    def dbToRelPath(self, sDbPath):

        sDbPath = pathNorm(sDbPath)
        sRelPath = pathRelativeTo(sDbPath, pathNorm(self.dbPath()))
        return sRelPath

    def allowFreePublish(self):
        return self.getVar("free_publish", False)

    def getHomonym(self, sSpace, weak=False, create=False):

        if self.space == sSpace:
            return self

        return self.project.getLibrary(sSpace, self.sectionName)

    def getVar(self, sVarName, default="NoEntry", **kwargs):
        return self.project.getVar(self.sectionName, sVarName, default=default, **kwargs)

    def suppress(self):
        raise RuntimeError("You cannot delete a library !!")

    def sendToTrash(self):
        raise RuntimeError("You cannot delete a library !!")

    def _addDbNodeToCache(self, dbnode):

        sDbPath = dbnode.file

#        sAbsPath = self.dbToAbsPath(sDbPath)
#        if not self.contains(sAbsPath):
#            raise AssertionError(u"{} path not contained in {}: '{}'."
#                                 .format(dbnode, self, sDbPath))

        dbCacheKey = normCase(sDbPath)
        logMsg(u"caching: '{}'".format(dbCacheKey), log='debug')

        self._cachedDbNodes[dbCacheKey] = dbnode

    def _weakDir(self, pathOrInfo, **kwargs):
        return self.getEntry(pathOrInfo, weak=True, drcType=self.__class__.classDir,
                             **kwargs)

    def _weakFile(self, pathOrInfo, **kwargs):
        return self.getEntry(pathOrInfo, weak=True, drcType=self.__class__.classFile,
                             **kwargs)

    def _remember(self):

        DrcEntry._remember(self)

        libCacheKey = self.fullName
        cacheDict = self.project.loadedLibraries

        if libCacheKey in cacheDict:
            logMsg("<{}> Already loaded : {}.".format(getCaller(depth=4, fo=False), self)
                   , log="debug")
        else:
            cacheDict[libCacheKey] = self

    def _forget(self, parent=None):

        DrcEntry._forget(self, parent)

        libCacheKey = self.fullName
        cacheDict = self.project.loadedLibraries

        if libCacheKey not in cacheDict:
            logMsg("<{}> Already dropped : {}.".format(getCaller(depth=4, fo=False), self), log="debug")
        else:
            return cacheDict.pop(libCacheKey)

