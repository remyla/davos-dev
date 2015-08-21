
import os
import os.path as osp

#from pytd.core.metaproperty import MetaProperty, BasePropertyFactory
from pytd.core.metaobject import MetaObject
#
#class DamBaseProperty(MetaProperty):
#
#    def __init__(self, sProperty, metaobj):
#        super(DamBaseProperty, self).__init__(sProperty, metaobj)
#
#class PropertyFactory(BasePropertyFactory):
#
#    propertyTypeDct = {
#    'dam_base' : DamBaseProperty,
#    }
#
#
#class DamMetaObject(MetaObject):
#    propertyFactoryClass = PropertyFactory

from pytd.util.fsutils import iterPaths, ignorePatterns, copyFile
from pytd.util.fsutils import pathParse, normCase
from pytd.util.external import parse


class DamUser(MetaObject):

    def __init__(self, proj, userData):

        self.loginName = userData["login"]
        self.name = userData.get("name", self.loginName)


class DamEntity(MetaObject):

    parentEntityAttr = "parent"
    nameFormat = "{baseName}"

    @classmethod
    def fromPath(cls, proj, sConfSection, sEntryPath):

        drcEntry = proj.entryFromPath(sEntryPath)

        pubEntry = drcEntry if drcEntry.isPublic() else drcEntry.getPublicFile()
        sPublicPath = pubEntry.absPath()

        sTemplatePath = proj.getPath("public", sConfSection, "entity_dir",
                                     resVars=False)

        print sTemplatePath
        print sPublicPath
        print ""
        parseRes = pathParse(sTemplatePath, sPublicPath)

        data = parseRes.named
        data["section"] = sConfSection

        return cls(proj, **data)

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

    def getEntry(self, sSpace, pathVar="entity_dir", **kwargs):
        p = self.getPath(sSpace, pathVar=pathVar, **kwargs)
        return self.project.entryFromPath(p)

    def getPath(self, sSpace, pathVar="entity_dir", **kwargs):
        return self.project.getPath(sSpace, self.confSection, pathVar,
                                    tokens=vars(self), **kwargs)

    def getTemplatePath(self, pathVar="entity_dir", **kwargs):
        return self.project.getTemplatePath(self.confSection, "entity_dir", **kwargs)

    def resourceFromPath(self, sEntryPath):

        proj = self.project

        drcEntry = proj.entryFromPath(sEntryPath)
        if not drcEntry:
            return "", ""

        pubEntry = drcEntry if drcEntry.isPublic() else drcEntry.getPublicFile()
        if not pubEntry:
            raise RuntimeError("Could not get public version of '{}'"
                               .format(sEntryPath))

        sPublicPath = normCase(pubEntry.absPath())

        pathIter = proj.iterPaths("public", self.confSection, tokens=vars(self))
        for sVar, sPath in pathIter:
            if normCase(sPath) == sPublicPath:
                return sVar, sPath

    def parentEntity(self):
        return getattr(self, self.__class__.parentEntityAttr)


class DamAsset(DamEntity):

    parentEntityAttr = "assetType"
    nameFormat = "{assetType}_{baseName}_{variation}"

    def __init__(self, proj, **kwargs):
        super(DamAsset, self).__init__(proj, **kwargs)
        if not self.confSection:
            self.confSection = self.assetType

    def createDirsAndFiles(self, sSpace="public", **kwargs):

        bDryRun = kwargs.get("dry_run", False)

        sAstName = self.name

        sTemplatePath = self.getTemplatePath()
        if not sTemplatePath:
            return []

        print '\nCreating {} directories for "{}":'.format(sSpace.upper(), sAstName)
        sDestAstDir = self.getPath(sSpace)

        if not (bDryRun or osp.isdir(sDestAstDir)):
            os.makedirs(sDestAstDir)

        createdList = []

        srcPathItr = iterPaths(sTemplatePath, ignoreFiles=ignorePatterns("*.db", ".*"))
        for sSrcPath in srcPathItr:
            sDestPath = (sSrcPath.replace(sTemplatePath, sDestAstDir)
                         .replace("{name}", sAstName))

            if not osp.exists(sDestPath):
                print "\t", sDestPath

                if not bDryRun:
                    if sDestPath.endswith("/"):
                        os.mkdir(sDestPath)
                    else:
                        copyFile(sSrcPath, sDestPath, **kwargs)

                createdList.append(sDestPath)

        return createdList


class DamShot(DamEntity):

    parentEntityAttr = "sequence"
    nameFormat = "{sequence}_{baseName}"

    def __init__(self, proj, **kwargs):
        print kwargs
        super(DamShot, self).__init__(proj, **kwargs)
        if not self.confSection:
            self.confSection = "shot_lib"


