
import os
import os.path as osp

from pytd.util.pyconfparser import PyConfParser
from pytd.util.logutils import logMsg
from pytd.util.fsutils import pathJoin, pathResolve, pathNorm
from pytd.util.strutils import findFields
from pytd.util import sysutils
from pytd.util.sysutils import argToTuple, isQtApp
from pytd.gui.dialogs import confirmDialog

from .drclibrary import DrcLibrary
from .damtypes import DamUser
from .authtypes import HellAuth
from .utils import getConfigModule

LIBRARY_SPACES = ("public", "private")

"""
from pytd.util.fsutils import pathJoin
from davos.core import damproject
reload(damproject)

DamProject = damproject.DamProject

proj = DamProject("zombillenium")

sAssetName = "chr_actionnaire1"
p = proj.getPath("public","asset_lib","master_file", tokens={"assetType":"chr","asset":sAssetName})

entry = proj.entryFromPath(p)
privFile = entry.edit()

#entry.nextVersionName()
#entry.getLatestBackupFile()

proj.publishEditedVersion(privFile.absPath())

"""

class DamProject(object):

    def __new__(cls, sProjectName, **kwargs):
        logMsg(cls.__name__ , log='all')

        proj = object.__new__(cls)

        proj.reset()
        proj.name = sProjectName
        proj.__libraryType = kwargs.pop("libraryType", DrcLibrary)

        if kwargs.pop("empty", False):
            return proj

        if not proj.init():
            return None

        proj.loadLibraries()

        return proj

    def reset(self):
        logMsg(log='all')

        self._damasdb = None
        self._shotgundb = None
        self._authobj = None
        self._itemmodel = None
        self.__loggedUser = None

        self.authenticated = False
        self.loadedLibraries = {}

    def init(self, **kwargs):
        logMsg(log='all')

        self.reset()

        try:
            self.__confobj = PyConfParser(getConfigModule(self.name))
        except ImportError, msg:
            if kwargs.pop("warn", True):
                logMsg(msg , warning=True)
            return False

        self.__confLibraries = self.getVar("project", "libraries")

        sMissingPathList = []
        self._checkTemplatePaths(sMissingPathList)
        if sMissingPathList:
            msg = "Missing template paths:\n\t" + '\n\t'.join(sMissingPathList)
            logMsg(msg , warning=True)
            return False

        self.__initShotgun()
        self.__initDamas()

        return self.authenticate()

    def authenticate(self):

        self._authobj = self.getAuthenticator()
        userData = self._authobj.authenticate()

        if not self.isAuthenticated():
            return False

        self.__loggedUser = DamUser(self, userData)
        os.environ["DAM_USER"] = self.__loggedUser.loginName

        return True

    def getAuthenticator(self):

        sAuthFullName = self.getVar("project", "authenticator", "")
        if not sAuthFullName:
            return HellAuth()
        else:
            sAuthMod, sAuthClass = sAuthFullName.rsplit(".", 1)
            exec("from {} import {}".format(sAuthMod, sAuthClass))

            return eval(sAuthClass)(self)

    def isAuthenticated(self):

        if not self._authobj:
            return False

        bAuth = self._authobj.authenticated

        if not bAuth:
            logMsg("The project is not authenticated.", warning=True)

        return bAuth

    def loggedUser(self, **kwargs):
        logMsg(log='all')

        bForce = kwargs.get("force", False)

        if bForce and not self.isAuthenticated():
            self.authenticate(relog=True)

        return self.__loggedUser

    def loadLibraries(self, noError=False):
        logMsg(log='all')

        if not self.isAuthenticated():
            return

        if not self._checkLibraryPaths(noError=noError):
            return

        bDevMode = sysutils.inDevMode()

        for sSpace, sLibName in self._iterConfigLibraries():

            drcLib = self.getLibrary(sSpace, sLibName)
            if not drcLib:
                continue

            if (not bDevMode) and sSpace == "private":
                continue

            drcLib.addModelRow()

    def getLibrary(self, sSpace, sLibName):
        logMsg(log='all')

        self._assertSpaceAndLibName(sSpace, sLibName)

        sFullLibName = DrcLibrary.makeFullName(sSpace, sLibName)
        drcLib = self.loadedLibraries.get(sFullLibName, None)

        if not drcLib:
            sLibPath = self.getPath(sSpace, sLibName)
            if osp.isdir(sLibPath):
                drcLib = self.__libraryType(sLibName, sLibPath, sSpace, self)
            else:
                logMsg("No such '{}': '{}'.".format(sFullLibName, sLibPath),
                       warning=True)

        return drcLib

    def iterPaths(self, sSpace, sLibName, tokens=None, **kwargs):

        for sPathVar in self.getVar(sLibName, "all_path_vars", ()):

            p = self.getPath(sSpace, sLibName, pathVar=sPathVar,
                             tokens=tokens, **kwargs)
            if not p:
                continue

            yield p

    def getPath(self, sSpace, sLibName, pathVar="", tokens=None, **kwargs):

        if sSpace in LIBRARY_SPACES:
            sRcPath = self.getVar(sLibName, sSpace + "_path")
        else:
            sRcPath = self.getVar(sLibName, sSpace + "_path", default="")
            if not sRcPath:
                return sRcPath

        if pathVar:
            sRcPath = pathJoin(sRcPath, self.getVar(sLibName, pathVar))

        if kwargs.get("resEnvs", True):
            sRcPath = pathResolve(sRcPath)

        if not kwargs.get("resVars", True):
            return sRcPath

        # resolve vars from config
        sFieldSet = set(findFields(sRcPath))
        if sFieldSet:
            sVarFields = set(f for f in sFieldSet if self.hasVar(sLibName, f))
            if sVarFields:
                confTokens = dict((f, self.getVar(sLibName, f, '{' + f + '}'))
                                  for f in sFieldSet)
                if confTokens:
                    sRcPath = sRcPath.format(**confTokens)

                sFieldSet -= sVarFields

        # resolve remaining vars from input tokens
        if tokens and isinstance(tokens, dict):

            rest = sFieldSet - set(tokens.iterkeys())
            if rest:
                msg = ("Cannot resolve path: '{}'. \n\tMissing tokens: {}"
                        .format(sRcPath, list(rest)))
                raise AssertionError(msg)

            return sRcPath.format(**tokens)

        return sRcPath

    def getVar(self, sSection, sVarName, default="NoEntry", **kwargs):
        return self.__confobj.getVar(sSection, sVarName, default=default, **kwargs)

    def hasVar(self, sSection, sVarName):
        return self.__confobj.hasVar(sSection, sVarName)

    def libraryFromPath(self, sEntryPath):

        sPath = pathNorm(sEntryPath)

        for drcLib in self.loadedLibraries.itervalues():
            if drcLib.contains(sPath):
                return drcLib

    def entryFromPath(self, sEntryPath, **kwargs):

        drcLib = self.libraryFromPath(sEntryPath)
        assert drcLib is not None, "Path is NOT from a KNOWN library !"

        return drcLib.getEntry(sEntryPath, **kwargs)

    def publishEditedVersion(self, sSrcFilePath, **kwargs):

        privFile = self.entryFromPath(sSrcFilePath)
        pubFile = privFile.getPublicFile()
        pubFile.assertFilePublishable(privFile)
        pubFile.incrementVersion(privFile, **kwargs)

    def listUiClasses(self):
        return DrcLibrary.listUiClasses()

    def setItemModel(self, model):
        self._itemmodel = model
        for lib in self.loadedLibraries.itervalues():
            lib.setItemModel(model)

    def iterChildren(self):
        return self.loadedLibraries.itervalues()

    def _checkLibraryPaths(self, noError=False):

        sMissingPathList = []

        for sSpace, sLibName in self._iterConfigLibraries():

            sLibPath = self.getPath(sSpace, sLibName)
            if not osp.isdir(sLibPath):

                sLibFullName = DrcLibrary.makeFullName(sSpace, sLibName)
                if sSpace == "public":
                    msg = "No such '{}': '{}'.".format(sLibFullName, sLibPath)
                    if noError:
                        logMsg(msg, warning=True)
                    else:
                        raise RuntimeError(msg)
                elif sSpace == "private":
                    sMissingPathList.append((sLibFullName, sLibPath))

        if sMissingPathList:

            msgIter = (u"'{}': '{}'".format(n, p) for n, p in sMissingPathList)
            msg = u"No such libraries:\n\n" + u"\n".join(msgIter)

            if isQtApp():
                sConfirm = confirmDialog(title='WARNING !',
                                         message=msg,
                                         button=['OK', 'Cancel'],
                                         defaultButton='Cancel',
                                         cancelButton='Cancel',
                                         dismissString='Cancel',
                                         icon="warning")

                if sConfirm == 'Cancel':
                    logMsg("Cancelled !", warning=True)
                    return False
            else:
                logMsg(msg, warning=True)
                res = ""
                while res not in ("yes", "no"):
                    res = raw_input("Should I create them ? (yes/no)")

                if res == "no":
                    return False

            for _, p in sMissingPathList:
                os.makedirs(p)

        return True

    def _checkTemplatePaths(self, out_invalidPaths, sSection="project"):

        for p in self.iterPaths("template", sSection):

            if osp.exists(p):
                continue

            out_invalidPaths.append(p)

        for sChildSection in self.getVar(sSection, "child_sections", ()):
            self._checkTemplatePaths(out_invalidPaths, sChildSection)

    def _assertSpaceAndLibName(self, sSpace, sLibName):

        if sSpace not in LIBRARY_SPACES:
            raise ValueError("No such space: '{}'. Expected: {}"
                            .format(sSpace, LIBRARY_SPACES))

        if sLibName not in self.__confLibraries:
            msg = ("No such library: '{}'. \n\n\tKnown libraries: {}"
                   .format(sLibName, self.__confLibraries))
            raise ValueError(msg)

    def _iterConfigLibraries(self, space=LIBRARY_SPACES, fullName=False):

        sSpaceList = argToTuple(space)

        for sLibName in self.__confLibraries:
            for sSpace in sSpaceList:
                if fullName:
                    yield DrcLibrary.makeFullName(sSpace, sLibName)
                else:
                    yield (sSpace, sLibName)

    def __initShotgun(self):

        if self.getVar("project", "no_shotgun", False):
            return

        print "connecting to shotgun..."

        from zompy.shotgunengine import ShotgunEngine
        self._shotgundb = ShotgunEngine(self.name)

    def __initDamas(self):

        if self.getVar("project", "no_damas", False):

            from .dbtypes import DummyDbCon
            self._damasdb = DummyDbCon()
            return

        print "connecting to damas..."

        from davos.core import damas
        self._damasdb = damas.http_connection("http://62.210.104.42:8090")


    def __repr__(self):

        cls = self.__class__

        try:
            sRepr = ("{0}('{1}')".format(cls.__name__, self.name))
        except AttributeError:
            sRepr = cls.__name__

        return sRepr
