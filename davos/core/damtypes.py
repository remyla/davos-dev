
import os
import os.path as osp

from pytd.util.fsutils import iterPaths, ignorePatterns, copyFile
from pytd.util.fsutils import normCase
from pytd.util.external import parse
from pytd.util.sysutils import isQtApp



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

        pathIter = proj.iterPaths("public", self.confSection, tokens=vars(self))
        for sVar, sPath in pathIter:
            if normCase(sPath) == sPublicPath:
                return sVar, sPath

    def parentEntity(self):
        return getattr(self, self.__class__.parentEntityAttr)

    def createDirsAndFiles(self, sSpace="public", **kwargs):

        bDryRun = kwargs.get("dry_run", False)

        sEntityName = self.name

        sTemplatePath = self.getTemplatePath()
        if not sTemplatePath:
            return []

        print '\nCreating {} directories for "{}":'.format(sSpace.upper(), sEntityName)
        sEntityDirPath = self.getPath(sSpace)

        if not (bDryRun or osp.isdir(sEntityDirPath)):
            os.makedirs(sEntityDirPath)

        createdList = []

        srcPathItr = iterPaths(sTemplatePath, ignoreFiles=ignorePatterns("*.db", ".*"))
        for sSrcPath in srcPathItr:
            sDestPath = (sSrcPath.replace(sTemplatePath, sEntityDirPath)
                         .format(**vars(self)))

            if not osp.exists(sDestPath):
                print "\t", sDestPath

                if not bDryRun:
                    if sDestPath.endswith("/"):
                        os.mkdir(sDestPath)
                    else:
                        copyFile(sSrcPath, sDestPath, **kwargs)

                createdList.append(sDestPath)

        return createdList

    def getSgInfo(self):
        raise NotImplementedError("Must be implemented in sub-classes")

    def getSgStep(self, sStepCode):

        for sgStep in self.project.iterSgSteps(self.__class__.sgEntityType):
            if sStepCode and (sgStep['code'] == sStepCode):
                return sgStep

    def listSgTasks(self, sStepCode, b_inMyTasks=False):

        proj = self.project

        sgEntity = self.getSgInfo()
        sgStep = self.getSgStep(sStepCode)

        filters = [
                    ['entity', 'is', sgEntity],
                    ['step', 'is', sgStep]
                ]

        if b_inMyTasks:
            filters.append(['sg_operators', 'contains', proj._shotgundb.currentUser])

        """
        {
            "filter_operator": "any",
            "filters": [
                [ "sg_status_list", "is", "rdy"],
                [ "sg_status_list", "is", "ip" ]
            ]
        }
        """

        fields = ['content', 'entity']#, 'step', 'entity', 'project', 'sg_status_list', 'sg_operators']
        tasks = proj._shotgundb.sg.find("Task", filters, fields)

        return tasks

    def createSgVersion(self, drcPubFile, iVersion, sComment, sgTask=None):

        sVersionName = osp.splitext(drcPubFile.nameFromVersion(iVersion))[0]

        if sgTask is None:

            sSgStep = drcPubFile.getParam('sg_step', "")
            if not sSgStep:
                raise RuntimeError("No Shotgun Step defined for {}".format(drcPubFile))

            sgTaskList = self.listSgTasks(sSgStep)
            if not sgTaskList:
                raise RuntimeError("No Shotgun Tasks found for {}".format(self))

            if len(sgTaskList) == 1:
                taskNameOrInfo = sgTaskList[0]
            else:
                sgTaskDct = dict((sg['content'], sg) for sg in sgTaskList)
                sTaskList = sgTaskDct.keys()

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
                    sChoiceList = sTaskList + ["Cancel"]
                    sMsg += "({})".format("/".join(sChoiceList))
                    sChoice = ""
                    while sChoice not in sChoiceList:
                        sChoice = raw_input(sMsg)

                    if sChoice == "Cancel":
                        raise RuntimeError("No task selected !")

                    sTaskName = sChoice

                taskNameOrInfo = sgTaskDct[sTaskName]

            entityNameOrInfo = taskNameOrInfo.pop('entity')
        else:
            taskNameOrInfo = sgTask
            if isinstance(sgTask, basestring):
                entityNameOrInfo = self.name
            elif isinstance(sgTask, dict):
                entityNameOrInfo = sgTask.pop('entity')
            else:
                raise TypeError("Bad 'sgTask' argument.")

        return self.project.createSgVersion(entityNameOrInfo,
                                            sVersionName,
                                            taskNameOrInfo,
                                            sComment)

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
        res = self.project._shotgundb.getAssetsInfo(self.name)
        return res[0] if res else None


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


