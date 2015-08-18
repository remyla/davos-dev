
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

from pytd.util.fsutils import pathParsed, normCase
from pytd.util.external import parse


class DamUser(object):

    def __init__(self, proj, userData):

        self.loginName = userData["login"]
        self.name = userData.get("name", self.loginName)


class DamEntity(MetaObject):

    def __init__(self, proj, **kwargs):
        self.project = proj
        self.name = kwargs["name"]

class DamAsset(DamEntity):

    @classmethod
    def fromPath(cls, proj, sConfSection, sEntryPath):

        drcEntry = proj.entryFromPath(sEntryPath)

        pubEntry = drcEntry if drcEntry.isPublic() else drcEntry.getPublicFile()
        sPublicPath = pubEntry.absPath()

        sTemplatePath = proj.getPath("public", sConfSection, "entity_dir", resVars=False)
        parseRes = pathParsed(sTemplatePath, sPublicPath)

        return cls(proj, **parseRes.named)

    def __init__(self, proj, **kwargs):
        super(DamAsset, self).__init__(proj, **kwargs)

        fmt = "{assetType}_{baseName}_{variation}"
        parseRes = parse.parse(fmt, self.name)
        if not parseRes:
            raise ValueError("Invalid asset name: '{}'".format(self.name))

        sAstType = kwargs.get("assetType", "")
        if not sAstType:
            sAstType = parseRes["assetType"]
        else:
            if sAstType != parseRes["assetType"]:
                msg = "Mismatch between name and assetType: {}.assetType = '{}' !"
                raise ValueError(msg.format(self, sAstType))

        self.assetType = sAstType
        self.baseName = parseRes["baseName"]
        self.variation = parseRes["variation"]

    def getPath(self, sSpace, pathVar="entity_dir", **kwargs):
        return self.project.getPath(sSpace, self.assetType, pathVar, tokens=vars(self), **kwargs)

    def getTemplatePath(self, pathVar="entity_dir", **kwargs):
            return self.project.getTemplatePath(self.assetType, "entity_dir", **kwargs)

    def resourceFromPath(self, sEntryPath):

        proj = self.project

        drcEntry = proj.entryFromPath(sEntryPath)
        pubEntry = drcEntry if drcEntry.isPublic() else drcEntry.getPublicFile()
        sPublicPath = pubEntry.absPath()

        for sVar, sPath in proj.iterPaths("public", self.assetType, tokens=vars(self)):
            if normCase(sPath) == normCase(sPublicPath):
                return sVar, sPath

