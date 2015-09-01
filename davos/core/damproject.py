
import os
import os.path as osp
import re

from pytd.util.pyconfparser import PyConfParser
from pytd.util.logutils import logMsg
from pytd.util.fsutils import pathJoin, pathResolve, pathNorm, normCase
from pytd.util.fsutils import pathSplitDirs, pathParse
from pytd.util.strutils import findFields
from pytd.util import sysutils
from pytd.util.sysutils import argToTuple, isQtApp, importClass, hostApp
from pytd.gui.dialogs import confirmDialog
#from pytd.util.external import parse

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

    def __new__(cls, sProjectName, **kwargs):
        logMsg(cls.__name__ , log='all')

        proj = object.__new__(cls)

        proj.reset()
        proj.name = sProjectName

        libClass = DrcLibrary
        if hostApp() == "maya":
            try:
                from davos_maya.core.mrclibrary import MrcLibrary
            except ImportError:
                pass
            else:
                libClass = MrcLibrary

        proj.__libClass = libClass#kwargs.pop("libraryType", DrcLibrary)

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
            self._confobj = PyConfParser(getConfigModule(self.name))
        except ImportError, msg:
            if kwargs.pop("warn", True):
                logMsg(msg , warning=True)
            return False

        self.__confLibraries = self.getVar("project", "libraries")

        sMissingPathList = []
        self._checkTemplatePaths(sMissingPathList)
        if sMissingPathList:
            msg = "Missing template paths:\n    " + '\n    '.join(sMissingPathList)
            logMsg(msg , warning=True)
            #return False

        self.__initShotgun()
        self.__initDamas()

        return self.authenticate()

    def authenticate(self):

        self._authobj = self.getAuthenticator()
        userData = self._authobj.authenticate()

        if not self.isAuthenticated():
            return False

        self.__loggedUser = DamUser(self, userData)
        sLogin = self.__loggedUser.loginName
        os.environ["DAVOS_USER"] = sLogin

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
                drcLib = self.__libClass(sLibName, sLibPath, sSpace, self, dbNode=False)
            else:
                logMsg("No such '{}': '{}'.".format(sFullLibName, sLibPath),
                       warning=True)

        return drcLib

    def getPath(self, sSpace, sSection, pathVar="", tokens=None, default="NoEntry", **kwargs):

        if sSpace in LIBRARY_SPACES:
            sRcPath = self.getVar(sSection, sSpace + "_path")
        else:
            sRcPath = self.getVar(sSection, sSpace + "_path", default="")
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
        sFieldSet = set(findFields(sRcPath))
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

    def hasVar(self, sSection, sVarName):
        return self._confobj.hasVar(sSection, sVarName)

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

    def entryFromPath(self, sEntryPath, **kwargs):

        drcLib = self.libraryFromPath(sEntryPath)
        if not drcLib:
            msg = "Path is NOT from a KNOWN library: '{}'".format(sEntryPath)
            logMsg(msg, warning=True)
            return None

        return drcLib.getEntry(sEntryPath, **kwargs)

    def libraryFromPath(self, sEntryPath):

        sPath = pathNorm(sEntryPath)

        for drcLib in self.loadedLibraries.itervalues():
            if drcLib.contains(sPath):
                return drcLib

        return None

    def entityFromPath(self, sEntryPath):

        data = self.dataFromPath(sEntryPath)
        sSection = data.get('section')
        if not sSection:
            return None

        sEntityCls = self.getVar(sSection, "entity_class", default="")
        if not sEntityCls:
            return None

        cls = importClass(sEntityCls, globals(), locals())
        return cls(self, **data)

    def dataFromPath(self, sEntryPath):

        sSpace, sConfSection = self.sectionFromPath(sEntryPath)
        if not sConfSection:
            return {}

        drcEntry = self.entryFromPath(sEntryPath)
        pubEntry = drcEntry if drcEntry.isPublic() else drcEntry.getPublicFile(fail=True)

        sPublicPath = pubEntry.absPath()
        sPubPathDirs = pathSplitDirs(sPublicPath)
        numDirs = len(sPubPathDirs)

        sConfPathList = sorted(self.iterPaths("public", sConfSection, resVars=False),
                                   key=lambda x: len(x[1]),
                                   reverse=True)

        parseRes = None
        for sRcName, sConfPath in sConfPathList:

            parseRes = pathParse(sConfPath, sPublicPath)
            if parseRes and parseRes.named:
                break

        if not parseRes:
            return {}

        data = parseRes.named
        data["section"] = sConfSection
        data["space"] = sSpace

        if numDirs == len(pathSplitDirs(sConfPath)):
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

        privFile = self.entryFromPath(sSrcFilePath)

        privOutcomeItemsList = []
        missingList = []
        for sRcName, outFile in privFile.iterEditedOutcomeFiles():
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

        primeFile = privFile.getPublicFile(fail=True)
        primeFile.ensureFilePublishable(privFile)

        iNxtVers = primeFile.currentVersion + 1
        pubOutcomeList = self._prepareToPublish(privOutcomeList, version=iNxtVers)

        _, sgVersionInfo = primeFile.incrementVersion(privFile, **kwargs)

        for pubOutcomeFile, privOutcomeFile in zip(pubOutcomeList, privOutcomeList):
            pubOutcomeFile.incrementVersion(privOutcomeFile, comment=primeFile.comment,
                                            version=iNxtVers)

        sRcToUpload = primeFile.getParam("upload_to_sg", "")
        uploadFile = privOutcomeDct.get(sRcToUpload, None)
        if uploadFile:
            logMsg("uploading file to shotgun: '{}'".format(uploadFile))
            self.uploadSgVersion(sgVersionInfo['id'], uploadFile.absPath())

        return primeFile, privOutcomeDct

    def _prepareToPublish(self, privFileList, version=None):

        pubFileList = []
        try:
            for privFile in privFileList:

                pubFile = privFile.getPublicFile(fail=True)
                pubFile.ensureFilePublishable(privFile, version=version)
                pubFile.ensureLocked(autoLock=True)
                pubFileList.append(pubFile)

        except:
            for pubFile in pubFileList:
                pubFile.restoreLockState()
            raise

        return pubFileList

    def iterSgSteps(self, sEntityType=""):

        stepList = self._shotgundb.getSteps()
        for stepInfo in stepList:
            if sEntityType and (stepInfo['entity_type'] == sEntityType):
                yield stepInfo

    def createSgVersion(self, sgEntity, s_inVersionName, sgTask, s_inComment=""):

        shotgundb = self._shotgundb
        if not shotgundb:
            return None

        sg = shotgundb.sg
        #s_inTaskName must be a task name, we could check prior to Shotgun calls...

        # Create the version
        data = {
                'project': {'type':'Project', 'id':shotgundb._getProjectId()},
                'code': s_inVersionName,
                'description': s_inComment,
                #'sg_path_to_frames': s_inMediaPath,
                'sg_status_list': 'rev',
                'entity': sgEntity,
                'sg_task': sgTask,
                }

        if shotgundb.currentUser['sg_user'] != None:
            data['user'] = shotgundb.currentUser['sg_user']

        return sg.create('Version', data)

    def uploadSgVersion(self, iVersionId, s_inMediaPath):

        # Use the ID from the previous result to update the newly created version calling sg.upload and specifying 'sg_uploaded_movie'
        if os.path.isfile(s_inMediaPath):
            return self._shotgundb.sg.upload('Version', iVersionId, s_inMediaPath,
                                             'sg_uploaded_movie')
        else:
            logMsg("No such media to upload: \n    '{}'".format(s_inMediaPath),
                   warning=True)

    def findDbNodes(self, sQuery="", **kwargs):

        sBaseQuery = u"file:/^{}/"

        sDamasPath = self.getVar("project", "damas_root_path")
        sBaseQuery = sBaseQuery.format(sDamasPath)
        sFullQuery = " ".join((sBaseQuery, sQuery))

        return self._db.findNodes(sFullQuery, **kwargs)

    def listUiClasses(self):
        return DrcLibrary.listUiClasses()

    def setItemModel(self, model):
        self._itemmodel = model
        for lib in self.loadedLibraries.itervalues():
            lib.setItemModel(model)

    def iterChildren(self):
        return self.loadedLibraries.itervalues()

    def iterPaths(self, sSpace, sSection, tokens=None, **kwargs):

        for sPathVar in self.getVar(sSection, "all_tree_vars", ()):

            p = self.getPath(sSpace, sSection, pathVar=sPathVar,
                             tokens=tokens, **kwargs)
            if not p:
                continue

            yield (sPathVar, p)

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

            if isQtApp():
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

            for _, p in self.iterPaths("template", sSection):

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
