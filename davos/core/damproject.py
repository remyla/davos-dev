
import os
import os.path as osp
import re
from fnmatch import fnmatch

from pytd.util.pyconfparser import PyConfParser
from pytd.util.logutils import logMsg
from pytd.util.fsutils import pathJoin, pathResolve, pathNorm, normCase
from pytd.util.fsutils import pathSplitDirs, pathParse
from pytd.util.strutils import findFmtFields
from pytd.util.sysutils import inDevMode, hostSetEnvFunc
from pytd.util.sysutils import argToTuple, qtGuiApp, importClass, hostApp, updEnv
from pytd.gui.dialogs import confirmDialog
from pytd.util.qtutils import setWaitCursor

from .drclibrary import DrcLibrary
from .damtypes import DamUser
from .authtypes import HellAuth
from .utils import getConfigModule
from .dbtypes import DrcDb


LIBRARY_SPACES = ("public", "private")

"""
from pytd.util.fsutils import pathJoin
from davos.core import damproject
reload(damproject)

DamProject = damproject.DamProject

proj = DamProject("zombillenium")

sAssetName = "chr_aton_default"
p = proj.getPath("public","chr","previz_scene", tokens={"name":sAssetName})

entry = proj.entryFromPath(p)
privFile = entry.edit()

#entry.nextVersionName()
#entry.getLatestBackupFile()

proj.publishEditedVersion(privFile.absPath())

"""

class DamProject(object):

    _instancesDct = {}

    def __new__(cls, sProjName, **kwargs):
        logMsg(cls.__name__ , log='all')

        sProjName = sProjName.lower()

        bExists = True
        proj = cls._instancesDct.get(sProjName)
        if not proj:
            bExists = False

            proj = object.__new__(cls)
            proj.name = sProjName

            libClass = DrcLibrary
            if "maya" in hostApp():
                try:
                    from davos_maya.core.mrclibrary import MrcLibrary
                except ImportError:
                    pass
                else:
                    libClass = MrcLibrary

            proj.__libClass = libClass#kwargs.pop("libraryType", DrcLibrary)

            proj.reset()

        if not kwargs.pop("empty", False):

            if not proj.init():
                return None

            proj.loadLibraries()

        if not bExists:
            cls._instancesDct[sProjName] = proj

        #print id(proj), proj

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

        try:
            self._confobj = PyConfParser(getConfigModule(self.name))
        except ImportError, msg:
            #if kwargs.pop("warn", True):
            logMsg(msg , warning=True)
            return False

        self.__confLibraries = self.getVar("project", "libraries")

    def init(self):
        logMsg(log='all')

        bExists = self._alreadyExists()
        if bExists and self.isAuthenticated():
            return True

        print "<{}> Initializing...".format(self)

        #self.reset()

        sMissingPathList = []
        self._checkTemplatePaths(sMissingPathList)
        if sMissingPathList:
            msg = "Missing template paths:\n    " + '\n    '.join(sMissingPathList)
            logMsg(msg , warning=True)
            #return False

        self.__initShotgun()
        self.__initDamas()

        return self.authenticate()

    def _alreadyExists(self):
        return id(self.__class__._instancesDct.get(self.name)) == id(self)

    def authenticate(self):

        self._authobj = self.getAuthenticator()
        userData = self._authobj.authenticate()

        if not self.isAuthenticated():
            return False

        self.__loggedUser = DamUser(self, userData)
        sLogin = self.__loggedUser.loginName
        updEnv("DAVOS_USER", sLogin, conflict="replace", usingFunc=hostSetEnvFunc())

        self._db = DrcDb(self._damasdb, sLogin)

        return True

    def getAuthenticator(self):

        sAuthFullName = self.getVar("project", "authenticator_class", "")
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

        if bForce and (not self.isAuthenticated()):
            self.authenticate(relog=True)

        return self.__loggedUser

    def loadLibraries(self, noError=False):
        logMsg(log='all')

        bExists = self._alreadyExists()
        if bExists and self.loadedLibraries:
            return

        if not self.isAuthenticated():
            return

        if not self._checkLibraryPaths(noError=noError):
            return

        print "<{}> Loading libraries...".format(self)

        bDevMode = inDevMode()

        for sSpace, sLibName in self._iterConfigLibraries():

            drcLib = self.getLibrary(sSpace, sLibName)
            if not drcLib:
                continue

            if (not bDevMode) and sSpace == "private":
                continue

            if drcLib.primeProperty().viewItems:
                drcLib.updModelRow()
            else:
                drcLib.addModelRow()

    def loadEnviron(self, force=False):

        sMsg = "\nLoading '{}' environment:".format(self.name)

        envFunc = hostSetEnvFunc()
        if envFunc:
            print sMsg, "(using {}.{})".format(envFunc.__module__, envFunc.__name__)
        else:
            print sMsg

#        sDirName = self.getVar("project", "dir_name")
#        updEnv("DAVOS_PROJECT_DIR", sDirName, conflict="replace", usingFunc=envFunc)

        sDavosUser = os.environ.get("DAVOS_USER")
        if sDavosUser:
            updEnv("DAVOS_USER", sDavosUser, conflict="replace", usingFunc=envFunc)

        sConflict = "replace" if force else "keep"
        for sSpace, sLibName in self._iterConfigLibraries():

            sEnvVars = self.getVar(sLibName, sSpace + "_path_envars", default=())

            for sVar in sEnvVars:
                updEnv(sVar, self.getPath(sSpace, sLibName, resEnvs=False),
                       conflict=sConflict, usingFunc=envFunc)

        print ''

    def getLibrary(self, sSpace, sLibName):
        logMsg(log='all')

        self._assertSpaceAndLibName(sSpace, sLibName)

        sFullLibName = DrcLibrary.makeFullName(sSpace, sLibName)
        drcLib = self.loadedLibraries.get(sFullLibName, None)

        if not drcLib:
            sLibPath = self.getPath(sSpace, sLibName)
            if osp.isdir(sLibPath):
                drcLib = self.__libClass(sLibName, sLibPath, sSpace,
                                         project=self, dbNode=True)
            else:
                logMsg("No such '{}': '{}'.".format(sFullLibName, sLibPath),
                       warning=True)

        return drcLib

    def getPath(self, sSpace, sSection, pathVar="", tokens=None, default="NoEntry", **kwargs):

        sRcPath = self.getVar(sSection, sSpace + "_path", default=default)
        if not sRcPath:
            return sRcPath

        if pathVar:
            try:
                sRcPath = pathJoin(sRcPath, self.getVar(sSection, pathVar))
            except AttributeError:
                if default != "NoEntry":
                    return default
                raise

        if kwargs.get("resEnvs", True):
            sRcPath = pathResolve(sRcPath)

        if not kwargs.get("resVars", True):
            return sRcPath

        # resolve vars from config
        sFieldSet = set(findFmtFields(sRcPath))
        if sFieldSet:

            confTokens = self.getVar(sSection, pathVar + "_tokens", default={})
            sConfFieldSet = set(confTokens.iterkeys())

            for sField in sFieldSet:

                if sField in confTokens:
                    continue

                value = self.getVar(sSection, sField, "")
                if value:
                    sConfFieldSet.add(sField)
                else:
                    value = '{' + sField + '}'

                confTokens[sField] = value

            if confTokens:
                sRcPath = sRcPath.format(**confTokens)

            sFieldSet -= sConfFieldSet

        # resolve remaining vars from input tokens
        if tokens:
            if not isinstance(tokens, dict):
                raise TypeError("argument 'tokens' must be of type <dict>. Got {}"
                                .format(type(tokens)))

            sFieldSet = sFieldSet - set(tokens.iterkeys())
            if sFieldSet:
                msg = ("Cannot resolve path: '{}'. \n\tMissing tokens: {}"
                        .format(sRcPath, list(sFieldSet)))
                raise RuntimeError(msg)

            return sRcPath.format(**tokens)

        return sRcPath

    def getVar(self, sSection, sVarName, default="NoEntry", **kwargs):
        return self._confobj.getVar(sSection, sVarName, default=default, **kwargs)

    def getRcParam(self, sSection, sRcName, sParam, default="NoEntry"):

        rcSettings = self.getVar(sSection, "resources_settings", {})

        if default == "NoEntry":
            return rcSettings[sRcName][sParam]
        else:
            return rcSettings.get(sRcName, {}).get(sParam, default)

    def getResource(self, sSpace, sRcSection, sRcName="", tokens=None,
                    default="NoEntry", fail=False, **kwargs):

        sRcPath = self.getPath(sSpace, sRcSection,
                               pathVar=sRcName,
                               tokens=tokens,
                               default=default,
                               )

        drcEntry = self.entryFromPath(sRcPath, **kwargs)

        if (not drcEntry) and fail:
            raise RuntimeError("No such resource path: '{}'".format(sRcPath))

        return drcEntry

    def isEditableResource(self, sAbsPath):

        sFileName = osp.basename(sAbsPath)
        if not sFileName:
            print "No filename"
            return False

        bPatternOk = False
        sPatterns = self.getVar("project", "editable_files", ())
        for sPatt in sPatterns:
            if fnmatch(sFileName, sPatt):
                bPatternOk = True
                break

        if not bPatternOk:
            return False

        data = self.dataFromPath(sAbsPath)

        sSection = data.get("section")
        sRcName = data.get("resource")

        if not sRcName:
            print "Not a resource"
            return False

        return self.getRcParam(sSection, sRcName, "editable", default=True)

    def entryFromPath(self, sEntryPath, space="", **kwargs):

        bFail = kwargs.pop('fail', False)

        drcLib = self.libraryFromPath(sEntryPath, space=space)
        if not drcLib:
            sLibType = space.upper() if space else "KNOWN"
            msg = "Path NOT from {} library: '{}'".format(sLibType, sEntryPath)

            if bFail:
                raise ValueError(msg)
            else:
                logMsg(msg, warning=True)
                return None

        return drcLib.getEntry(sEntryPath, **kwargs)

    def entryFromDbNode(self, dbnode, **kwargs):

        sDbPath = dbnode.getField('file')
        drcLib = self.libraryFromDbPath(sDbPath)
        return drcLib.entryFromDbPath(sDbPath, **kwargs)

    def libraryFromDbPath(self, sDbPath):

        for drcLib in self.loadedLibraries.itervalues():

            if not drcLib.isPublic():
                continue

            try:
                drcLib.dbToAbsPath(sDbPath)
            except ValueError:
                continue

            return drcLib

        return None

    def libraryFromPath(self, sEntryPath, space=""):

        p = pathNorm(sEntryPath)

        for drcLib in self.loadedLibraries.itervalues():

            if space and (drcLib.space != space):
                continue

            if drcLib.contains(p):
                return drcLib

        return None

    def entityFromPath(self, sEntryPath, fail=True):

        data = self.dataFromPath(sEntryPath)
        sSection = data.get('section')
        if not sSection:
            return None

        sEntityCls = self.getVar(sSection, "entity_class", default="")
        if not sEntityCls:
            return None

        cls = importClass(sEntityCls, globals(), locals())
        try:
            return cls(self, **data)
        except:
            if fail:
                raise
            return None

    def dataFromPath(self, sEntryPath):

        sSpace, sSection = self.sectionFromPath(sEntryPath)
        if not sSection:
            return {}

        drcEntry = self.entryFromPath(sEntryPath, weak=True)
        pubEntry = drcEntry
        if not drcEntry.isPublic():
            pubEntry = drcEntry.getPublicFile(fail=True, weak=True)

        sPublicPath = pubEntry.absPath()
        sPubPathDirs = pathSplitDirs(sPublicPath)
        numDirs = len(sPubPathDirs)

        sRcPathList = sorted(self.iterRcPaths("public", sSection, resVars=False),
                                   key=lambda x: len(x[1]),
                                   reverse=True)

        parseRes = None
        for sRcName, sRcPath in sRcPathList:

            parseRes = pathParse(sRcPath, sPublicPath)
            if parseRes and parseRes.named:
                break

        if not parseRes:
            return {}

        data = parseRes.named
        data["section"] = sSection
        data["space"] = sSpace

        if numDirs == len(pathSplitDirs(sRcPath)):
            data["resource"] = sRcName

        return data

    def sectionFromPath(self, sEntryPath):

        sEntryPath = normCase(sEntryPath)
        sEntryPathDirs = pathSplitDirs(normCase(sEntryPath))

        sectionDataList = sorted(self.iterSectionPaths(),
                                   key=lambda x: len(x[2]),
                                   reverse=True)

        for sSpace, sSection, sPath in sectionDataList:

            sSectionPath = normCase(sPath)

            numDirs = len(pathSplitDirs(sSectionPath))
            sAlignedPath = pathJoin(*sEntryPathDirs[:numDirs])

            if sAlignedPath == sSectionPath:
                return sSpace, sSection

        return "", ""

    def iterSectionPaths(self):

        for sSection, _ in self._confobj.listSections():

            if sSection == "project":
                continue

            for sSpace in LIBRARY_SPACES:
                sSectionPath = self.getPath(sSpace, sSection, default="")

                if sSectionPath:
                    yield sSpace, sSection, sSectionPath

    def publishEditedVersion(self, sSrcFilePath, **kwargs):

        mainPrivFile = self.entryFromPath(sSrcFilePath, space="private", fail=True)

        mainPubFile = mainPrivFile.getPublicFile(fail=True)

        mainPubFile.ensureFilePublishable(mainPrivFile)
        mainPubFile.ensureLocked()

        privOutcomeItemsList = []
        missingList = []
        for sRcName, outFile in mainPrivFile.iterEditedOutcomeFiles():
            if outFile.isFile():
                privOutcomeItemsList.append((sRcName, outFile))
            else:
                missingList.append((sRcName, outFile))

        if missingList:
            sMissingFiles = u"\n".join((u"'{}'".format(f.relPath())
                                        for rc, f in missingList))

            sMsg = u"Missing outcome files:\n\n{}\n\n".format(sMissingFiles)
            sMsg += u"Continue publishing without these outcome files ??"
            sResult = confirmDialog(title='WARNING !',
                                    message=sMsg,
                                    button=["Continue", "Abort"],
                                    defaultButton="Continue",
                                    cancelButton="Abort",
                                    dismissString="Abort",
                                    icon="warning")
            if sResult == "Abort":
                logMsg("Cancelled !", warning=True)
                return

        privOutcomeDct = dict(privOutcomeItemsList)
        privOutcomeList = privOutcomeDct.values()

        pubOutcomeList = tuple(f.getPublicFile(fail=True) for f in privOutcomeList)
        outcomePairs = zip(pubOutcomeList, privOutcomeList)

        sRcToUpload = mainPubFile.getParam("upload_to_sg", "")
        if sRcToUpload and privOutcomeDct:
            if sRcToUpload not in privOutcomeDct:

                sMsg = (u"Resource('{}') to upload to shotgun is NOT in outcomes: {}"
                        .format(sRcToUpload, privOutcomeDct.keys()))
                sResult = confirmDialog(title='WARNING !',
                                        message=sMsg,
                                        button=["Continue", "Abort"],
                                        defaultButton="Continue",
                                        cancelButton="Abort",
                                        dismissString="Abort",
                                        icon="warning")
                if sResult == "Abort":
                    logMsg("Cancelled !", warning=True)
                    return

        sgVersion = None
        iNxtVers = mainPubFile.currentVersion + 1
        try:
            for pubFile, privFile in outcomePairs:

                pubFile.ensureFilePublishable(privFile, version=iNxtVers)
                pubFile.ensureLocked(autoLock=True)

            _, sgVersion = mainPubFile.publishEditedFile(mainPrivFile, checkLock=False,
                                                         **kwargs)
        except:
            for pubFile in pubOutcomeList:
                pubFile.restoreLockState()
            raise

        for pubFile, privFile in outcomePairs:
            pubFile.publishEditedFile(privFile, comment=mainPubFile.comment,
                                      version=iNxtVers, checkLock=False)

        if sgVersion:
            uploadFile = privOutcomeDct.get(sRcToUpload, None)
            if uploadFile:
                logMsg("uploading file to shotgun: '{}'".format(uploadFile))
                self.uploadSgVersion(sgVersion, uploadFile.absPath())

        return mainPrivFile, privOutcomeDct

    def iterSgSteps(self, sEntityType=""):

        stepList = self._shotgundb.getSteps()
        for stepInfo in stepList:
            if sEntityType and (stepInfo['entity_type'] == sEntityType):
                yield stepInfo

    def createSgVersion(self, sVersionName, sgEntity, sgTask, sComment, sFilePath):

        shotgundb = self._shotgundb
        if not shotgundb:
            return None

        return shotgundb.createVersion(sgEntity["type"], sgEntity, sVersionName, sgTask,
                                       sComment, sFilePath)

    @setWaitCursor
    def uploadSgVersion(self, sgVersion, sMediaPath):
        return self._shotgundb.uploadVersion(sgVersion, sMediaPath)

    def findDbNodes(self, sQuery="", **kwargs):

        sBaseQuery = u"file:/^{}/i"

        sDamasPath = self.getVar("project", "damas_root_path")
        sBaseQuery = sBaseQuery.format(sDamasPath)
        sFullQuery = " ".join((sBaseQuery, sQuery))

        return self._db.findNodes(sFullQuery, **kwargs)

    def listAllSites(self):
        return ("dmn_paris", "dmn_angouleme", "online", "dream_wall", "pipangai")

    def listUiClasses(self):
        return DrcLibrary.listUiClasses()

    def setItemModel(self, model):
        self._itemmodel = model
        for lib in self.loadedLibraries.itervalues():
            lib.setItemModel(model)

    def iterChildren(self):
        return self.loadedLibraries.itervalues()

    def iterRcPaths(self, sSpace, sSection, tokens=None, **kwargs):

        allTreeVars = self.getVar(sSection, "all_tree_vars", ())
        #print sSection, len(allTreeVars), len(set(allTreeVars)), set(allTreeVars)
        for sTreeVar in allTreeVars:
            p = self.getPath(sSpace, sSection, pathVar=sTreeVar,
                             tokens=tokens, **kwargs)
            if not p:
                continue

            yield (sTreeVar, p)

    def _checkLibraryPaths(self, noError=False):

        sMissingPathList = []

        sSamePathDct = {}

        for sSpace, sLibName in self._iterConfigLibraries():

            sLibFullName = DrcLibrary.makeFullName(sSpace, sLibName)
            sLibPath = self.getPath(sSpace, sLibName)

            sSamePathDct.setdefault(normCase(sLibPath), []).append(sLibFullName)

            if not osp.isdir(sLibPath):

                if sSpace == "public":
                    msg = u"No such '{}': '{}'.".format(sLibFullName, sLibPath)
                    if noError:
                        logMsg(msg, warning=True)
                    else:
                        raise EnvironmentError(msg)
                elif sSpace == "private":
                    sMissingPathList.append((sLibFullName, sLibPath))

        sSamePathList = tuple((p, libs) for p, libs in sSamePathDct.iteritems() if len(libs) > 1)
        if sSamePathList:
            msgIter = (u"'{}': {}".format(p, libs) for p, libs in sSamePathList)
            msg = u"Libraries using the same path:\n\n    " + u"\n    ".join(msgIter)
            raise EnvironmentError(msg)

        if sMissingPathList:

            msgIter = (u"'{}': '{}'".format(n, p) for n, p in sMissingPathList)
            msg = u"No such libraries:\n" + u"\n".join(msgIter)

            if qtGuiApp():
                sConfirm = confirmDialog(title='WARNING !',
                                         message=msg + u"\n\n\tShould I create them ?",
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

    def getTemplatePath(self, sSection, pathVar="" , **kwargs):

        sTemplateDir = self.getPath("template", sSection, "template_dir", default="", **kwargs)
        if not sTemplateDir:
            return ""

        sEntityDir = self.getPath("template", sSection, "entity_dir", **kwargs)

        p = self.getPath("template", sSection, pathVar=pathVar, **kwargs)
        p = re.sub('^' + re.escape(sEntityDir), sTemplateDir, p)
        return p

    def _checkTemplatePaths(self, out_invalidPaths, sSection="project"):

        sTemplateDir = self.getTemplateDir(sSection)
        if sTemplateDir:

            sEntityDir = self.getPath("template", sSection, "entity_dir")

            for _, p in self.iterRcPaths("template", sSection):

                p = re.sub('^' + re.escape(sEntityDir), sTemplateDir, p)

                if osp.exists(p):
                    continue

                out_invalidPaths.append(p)

        for sChildSection in self.getVar(sSection, "child_sections", ()):
            self._checkTemplatePaths(out_invalidPaths, sChildSection)

    def getTemplateDir(self, sSection):
        return self.getPath("template", sSection, "template_dir", default="")

    def _assertSpaceAndLibName(self, sSpace, sLibName):

        if sSpace not in LIBRARY_SPACES:
            raise ValueError("No such space: '{}'. Expected: {}"
                            .format(sSpace, LIBRARY_SPACES))

        if sLibName not in self.__confLibraries:
            msg = ("No such library: '{}'. \n\n\tKnown libraries: {}"
                   .format(sLibName, self.__confLibraries))
            raise ValueError(msg)

    def assertMayaVersion(self, iCurMayaVersion):

        iProjMayaVersion = self.getVar("project", "maya_version")
        iCurMayaVersion /= 100

        if iCurMayaVersion != iProjMayaVersion:
            sMsg = ("{} requires Maya {}, but you're running Maya {} !"
                    .format(self, iProjMayaVersion, iCurMayaVersion))
            raise EnvironmentError(sMsg)

    def _iterConfigLibraries(self, space=LIBRARY_SPACES, fullName=False):

        sSpaceList = argToTuple(space)

        for sLibName in self.__confLibraries:
            for sSpace in sSpaceList:
                if fullName:
                    yield DrcLibrary.makeFullName(sSpace, sLibName)
                else:
                    yield (sSpace, sLibName)

    def __initShotgun(self):

        sFullName = self.getVar("project", "shotgun_class", "")
        if not sFullName:
            return

        cls = importClass(sFullName, globals(), locals())

        print "connecting to shotgun..."

        self._shotgundb = cls(self.name)

    def __initDamas(self):

        sDamasServerAddr = self.getVar("project", "damas_server_addr", "")
        if not sDamasServerAddr:

            from .dbtypes import DummyDbCon
            self._damasdb = DummyDbCon()
            return

        print "connecting to damas..."

        import damas
        self._damasdb = damas.http_connection(sDamasServerAddr)

    def __repr__(self):

        cls = self.__class__

        try:
            sRepr = ("{0}('{1}')".format(cls.__name__, self.name))
        except AttributeError:
            sRepr = cls.__name__

        return sRepr
