
import os
import os.path as osp
import re

from pytd.util.fsutils import iterPaths, ignorePatterns, copyFile
from pytd.util.fsutils import normCase
from pytd.util.external import parse
from pytd.util.sysutils import qtGuiApp, argToTuple
from pytd.util.strutils import assertChars


class DamUser(object):

    def __init__(self, proj, userData):

        self.loginName = userData["login"]
        self.name = userData.get("name", self.loginName)


class DamEntity(object):

    parentEntityAttr = "parent"
    nameFormat = "{baseName}"
    sgEntityType = "Entity"

    def __init__(self, proj, **kwargs):

        self.project = proj
        self.name = kwargs["name"]
        self.confSection = kwargs.get("section", "")

        cls = self.__class__

        fmt = cls.nameFormat
        nameParse = parse.parse(fmt, self.name)
        if not nameParse:
            raise ValueError("Invalid name: '{}'. Must match '{}' format."
                             .format(self.name, fmt))

        sParentAttr = cls.parentEntityAttr
        sParentName = kwargs.get(sParentAttr, "")
        if sParentAttr in nameParse:
            if not sParentName:
                sParentName = nameParse[sParentAttr]
            else:
                sParsedName = nameParse[sParentAttr]
                if sParentName != sParsedName:
                    msg = "Mismatch of '{}' between name and input arg: '{}' != '{}' !"
                    raise ValueError(msg.format(sParentAttr, sParsedName, sParentName))

        for k, v in nameParse.named.iteritems():

            if re.match("^[A-Z]", v):
                raise ValueError("Invalid name part: '{}'. Must NOT start with an uppercase !".format(v))

            assertChars(v, r"[a-zA-Z0-9]")
            setattr(self, k, v)

    def getResource(self, sSpace, sRcName="entity_dir", default="NoEntry", **kwargs):

        sRcPath = self.getPath(sSpace, pathVar=sRcName, default=default)
        return self.project.entryFromPath(sRcPath, **kwargs)

    def getPath(self, sSpace, pathVar="entity_dir", **kwargs):
        return self.project.getPath(sSpace, self.confSection, pathVar,
                                    tokens=vars(self), **kwargs)

    def getTemplatePath(self, pathVar="entity_dir", **kwargs):
        return self.project.getTemplatePath(self.confSection, pathVar=pathVar, **kwargs)

    def resourceFromPath(self, sEntryPath):

        proj = self.project

        drcEntry = proj.entryFromPath(sEntryPath)
        if not drcEntry:
            return "", ""

        pubEntry = drcEntry if drcEntry.isPublic() else drcEntry.getPublicFile(fail=True)

        sPublicPath = normCase(pubEntry.absPath())

        pathIter = proj.iterRcPaths("public", self.confSection, tokens=vars(self))
        for sVar, sPath in pathIter:
            if normCase(sPath) == sPublicPath:
                return sVar, sPath

    def parentEntity(self):
        return getattr(self, self.__class__.parentEntityAttr)

    def createDirsAndFiles(self, sSpace="public", **kwargs):

        bDryRun = kwargs.get("dry_run", True)

        sEntityName = self.name

        sTemplatePath = self.getTemplatePath()
        if not sTemplatePath:
            return []

        sAction = "Creating" if not bDryRun else "Missing"
        print '\n{} {} paths for "{}":'.format(sAction, sSpace.upper(), sEntityName)

        createdList = []

        sEntityDirPath = self.getPath(sSpace)
        if not osp.exists(sEntityDirPath):
            if not bDryRun:
                os.makedirs(sEntityDirPath)
            createdList.append(sEntityDirPath)

        srcPathItr = iterPaths(sTemplatePath, ignoreFiles=ignorePatterns("*.db", ".*"))
        for sSrcPath in srcPathItr:
            sDestPath = (sSrcPath.replace(sTemplatePath, sEntityDirPath)
                         .format(**vars(self)))

            if not osp.exists(sDestPath):
                print "\t", sDestPath

                if not bDryRun:
                    if sDestPath.endswith("/"):
                        os.makedirs(sDestPath)
                    else:
                        sDirPath = osp.dirname(sDestPath)
                        if not osp.exists(sDirPath):
                            os.makedirs(sDirPath)
                        copyFile(sSrcPath, sDestPath, **kwargs)

                createdList.append(sDestPath)

        return createdList

    def getSgInfo(self):
        raise NotImplementedError("Must be implemented in sub-classes")

    def getSgTasks(self, in_sStepCodes=None, fail=False):

        sStepCodes = argToTuple(in_sStepCodes)

        proj = self.project

        sgEntity = self.getSgInfo()
        sgSteps = None
        if sStepCodes:
            sgSteps = self.getSgSteps(*sStepCodes)

        sgTaskList = proj._shotgundb.getTasks(sgEntity, sgSteps)
        if (not sgTaskList) and fail:
            if sStepCodes:
                msg = ("<{}> No Shotgun Tasks found for given steps: {}"
                       .format(self, ", ".join(sStepCodes)))
            else:
                msg = "<{}> No Shotgun Task defined !".format(self)
            raise ValueError(msg)

        #sgTaskList.sort(key=lambda t:t['step']['list_order'])

        return sgTaskList

    def getSgSteps(self, *in_sStepCodes):

        sStepCodes = tuple(c.lower() for c in in_sStepCodes)

        sgStepIter = self.project.iterSgSteps(self.__class__.sgEntityType)

        if sStepCodes:
            return tuple(sgStep for sgStep in sgStepIter
                         if sgStep['code'].lower() in sStepCodes)
        else:
            return tuple(sgStepIter)

    def _sgTaskFromCode(self, sSgTaskCode, fail=False):

        shotgundb = self.project._shotgundb

        sgEntity = self.getSgInfo()
        sgTaskInfo = shotgundb._getTask(sSgTaskCode, sgEntity)
        if (not sgTaskInfo) and fail:
            sgTasks = shotgundb.getTasks(sgEntity)
            if not sgTasks:
                msg = "<{}> No Shotgun Task defined !".format(self)
            else:
                sTaskList = tuple(d["content"] for d in sgTasks)
                msg = ("<{}> No such Shotgun Task: '{}'. Are valid: {}."
                       .format(self, sSgTaskCode, sTaskList))
            raise ValueError(msg)

        return sgTaskInfo

    def chooseSgTask(self, sStepCodes=None, fromList=None):

        in_sTaskList = fromList
        if in_sTaskList:
            in_sTaskList = tuple(s.lower() for s in in_sTaskList)

        sgTaskList = self.getSgTasks(sStepCodes, fail=True)
        if len(sgTaskList) == 1:
            taskNameOrInfo = sgTaskList[0]
        else:
            sTaskList = list(d['content'] for d in sgTaskList)
            sgTaskDct = dict(zip(sTaskList, sgTaskList))

            if in_sTaskList:
                sTaskChoiceList = list(t for t in sTaskList if t.lower() in in_sTaskList)
                if not sTaskChoiceList:
                    raise ValueError("<{}> Unknown input tasks: {}. Are valid: {}."
                                     .format(self, in_sTaskList, sTaskList))
            else:
                sTaskChoiceList = sTaskList

            sMsg = "What was your task ?"
            if qtGuiApp():
                from PySide import QtGui
                sTaskName, bOk = QtGui.QInputDialog.getItem(None, "Make your choice !",
                                                            sMsg, sTaskChoiceList,
                                                            current=0,
                                                            editable=False)
                if not bOk:
                    raise RuntimeError("No task selected !")
            else:
                sChoiceList = sTaskChoiceList + ["Cancel"]
                sMsg += "({})".format("|".join(sChoiceList))
                sChoice = ""
                while sChoice not in sChoiceList:
                    sChoice = raw_input(sMsg)

                if sChoice == "Cancel":
                    raise RuntimeError("No task selected !")

                sTaskName = sChoice

            taskNameOrInfo = sgTaskDct[sTaskName]

        return taskNameOrInfo

    def listVersions(self):

        shotgundb = self.project._shotgundb
        if not shotgundb:
            return []

        filters = [
            ['project', 'is', {'type':'Project', 'id':shotgundb._getProjectId()}],
            ['entity', 'is', self.getSgInfo()]
        ]

        return shotgundb.sg.find("Version", filters,
                                 ['code', 'entity', 'sg_task'],
                                 [{'field_name':'code', 'direction':'asc'}])

    def showShotgunPage(self):
        self.project._shotgundb.showInBrowser(self.getSgInfo())

    def __repr__(self):

        cls = self.__class__

        try:
            sClsName = cls.__name__
            sRepr = "{}('{}')".format(sClsName, self.name)
        except AttributeError:
            sRepr = cls.__name__

        return sRepr


class DamAsset(DamEntity):

    parentEntityAttr = "assetType"
    nameFormat = "{assetType}_{baseName}_{variation}"
    sgEntityType = "Asset"

    def __init__(self, proj, **kwargs):
        super(DamAsset, self).__init__(proj, **kwargs)
        if not self.confSection:
            self.confSection = proj._confobj.getSection(self.assetType).name

    def getSgInfo(self):
        return self.project._shotgundb.getAssetInfo(self.name)


class DamShot(DamEntity):

    parentEntityAttr = "sequence"
    nameFormat = "{sequence}_{baseName}"
    sgEntityType = "Shot"

    def __init__(self, proj, **kwargs):
        super(DamShot, self).__init__(proj, **kwargs)
        if not self.confSection:
            self.confSection = "shot_lib"

    def getSgInfo(self):
        return self.project._shotgundb.getShotInfo(self.name)


