
import os.path as osp

from PySide.QtCore import QFileInfo

from pytd.util.logutils import logMsg

from pytd.util.sysutils import listClassesFromModule, getCaller
from pytd.util.qtutils import toQFileInfo
from pytd.util.fsutils import pathNorm, normCase, pathSplitDirs, pathJoin
from pytd.util import sysutils

from . import drctypes
from .drctypes import DrcEntry, DrcDir, DrcFile
from .dbtypes import DrcDb


class DrcLibrary(DrcEntry):

    classLabel = "library"
    classReprAttr = "fullName"
    classUiPriority = 0

    classFile = DrcFile
    classDir = DrcDir

    def __init__(self, sLibName, sLibPath, sSpace="", project=None):

        self._cachedEntries = {}
        self._cachedDbNodes = {}
        self._itemmodel = None
        self._db = None

        self.libName = sLibName
        self.fullName = DrcLibrary.makeFullName(sSpace, sLibName)
        self.space = sSpace
        self.project = project

        super(DrcLibrary, self).__init__(self, sLibPath)

    def loadData(self, fileInfo, **kwargs):
        logMsg(log="all")

        if self.project:
            self._itemmodel = self.project._itemmodel
            sUserLogin = self.project.loggedUser().loginName
            self._db = DrcDb(self.project._damasdb, sUserLogin)

        super(DrcLibrary, self).loadData(fileInfo, **kwargs)

        self.label = self.fullName if sysutils.inDevMode() else self.name

    def setItemModel(self, model):
        self._itemmodel = model

    def addModelRow(self):

        model = self._itemmodel
        if model:
            model.loadRowItems(self, model)

    @staticmethod
    def makeFullName(*names):
        return "|".join(names)

    @staticmethod
    def listUiClasses():
        return sorted((cls for (_, cls) in listClassesFromModule(drctypes.__name__)
                            if hasattr(cls, "classUiPriority")), key=lambda c: c.classUiPriority)

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
                            or <basestring>. Got {0}.".format(type(pathOrInfo)))

        # entries are cached using their relative path the the library they belong to.
        if not sRelPath:
            sRelPath = self.absToRelPath(sAbsPath) if osp.isabs(sAbsPath) else sAbsPath

        # try to get an already loaded entry...
        drcEntry = self._cachedEntries.get(sRelPath)
        if drcEntry:
            drcEntry.loadData(drcEntry._qfileinfo, dbNode=dbNode)
            if weak:
                return drcEntry
            else:
                return drcEntry if drcEntry.exists() else None

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

    def contains(self, sPath):

        sLibPath = normCase(self.absPath())
        sPathDirs = pathSplitDirs(normCase(sPath))

        numDirs = len(pathSplitDirs(sLibPath))
        sAlignedPath = pathJoin(*sPathDirs[:numDirs])

        return sAlignedPath == sLibPath

    def getHomonym(self, sSpace):

        if self.space == sSpace:
            return None

        return self.project.getLibrary(sSpace, self.libName)

    def getVar(self, sVarName, default="NoEntry", **kwargs):
        return self.project.getVar(self.libName, sVarName, default=default, **kwargs)

    def getConfPath(self, pathVar="", tokens=None):
        return self.project.getPath(self.space, self.libName, pathVar, tokens)

    def hasChildren(self):
        return True

    def suppress(self):
        raise RuntimeError("You cannot delete a library !!")

    def sendToTrash(self):
        raise RuntimeError("You cannot delete a library !!")

    def _weakDir(self, pathOrInfo):
        return self.getEntry(pathOrInfo, weak=True, drcType=self.__class__.classDir)

    def _weakFile(self, pathOrInfo):
        return self.getEntry(pathOrInfo, weak=True, drcType=self.__class__.classFile)

    def _remember(self):

        DrcEntry._remember(self)

        key = self.fullName
        cacheDict = self.project.loadedLibraries

        if key in cacheDict:
            logMsg("<{}> Already loaded : {}.".format(getCaller(depth=4, fo=False), self)
                   , log="debug")
        else:
            cacheDict[key] = self

    def _forget(self, parent=None):

        DrcEntry._forget(self, parent)

        key = self.fullName
        cacheDict = self.project.loadedLibraries

        if key not in cacheDict:
            logMsg("<{}> Already dropped : {}.".format(getCaller(depth=4, fo=False), self), log="debug")
        else:
            return cacheDict.pop(key)

