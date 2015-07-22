
import os.path as osp

from PySide.QtCore import QFileInfo

from pytd.util.logutils import logMsg

from pytd.util.sysutils import listClassesFromModule, getCaller
from pytd.util.qtutils import toQFileInfo
from pytd.util.fsutils import pathNorm
from pytd.util import sysutils

from . import drctypes
from .drctypes import DrcEntry, DrcDir, DrcFile
from .dbtypes import DrcDb


class DrcLibrary(DrcEntry):

    classLabel = "library"
    classReprAttr = "fullName"
    classUiPriority = 0

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

    def loadData(self, fileInfo):
        logMsg(log="all")

        if self.project:
            self._itemmodel = self.project._itemmodel
            self._db = DrcDb(self.project._damasdb)

        super(DrcLibrary, self).loadData(fileInfo)
        assert self.isDir(), "<{}> No such directory: '{}'".format(self, self.absPath())

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

        if not sRelPath:
            sRelPath = self.absToRelPath(sAbsPath) if osp.isabs(sAbsPath) else sAbsPath

        drcEntry = self._cachedEntries.get(sRelPath)
        if drcEntry:
            drcEntry.loadData(drcEntry._qfileinfo, dbNode=dbNode)
            if weak:
                return drcEntry
            else:
                return drcEntry if drcEntry.exists() else None

        if not fileInfo:
            fileInfo = toQFileInfo(sAbsPath)

        if weak:
            if drcType:
                cls = drcType
            else:
                cls = DrcDir if sAbsPath.endswith('/') else DrcFile
        else:
            if fileInfo.isDir():
                cls = DrcDir
            elif fileInfo.isFile():
                cls = DrcFile
            else:
                return None

        entry = cls(self, fileInfo, dbNode=dbNode)
        return entry

    def contains(self, sAbsPath):
        sLibPath = self.absPath()
        return (len(sAbsPath) >= len(sLibPath)) and sAbsPath.startswith(sLibPath)

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
        return self.getEntry(pathOrInfo, weak=True, drcType=DrcDir)

    def _weakFile(self, pathOrInfo):
        return self.getEntry(pathOrInfo, weak=True, drcType=DrcFile)

    def _remember(self):

        DrcEntry._remember(self)

        key = self.fullName
        cacheDict = self.project.loadedLibraries

        if key in cacheDict:
            logMsg("<{}> Already loaded : {}.".format(getCaller(depth=4, fo=False), self), log="debug")
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

