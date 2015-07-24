

from pytd.util.utiltypes import MemSize

from pytd.core.metaproperty import BasePropertyFactory
from pytd.core.metaproperty import MetaProperty
from pytd.core.metaproperty import EditState as Eds
from pytd.core.metaobject import MetaObject


DrcLibraryProperties = (
('label',
    {
    'type':'drc_base',
    'isMulti':False,
    'accessor':'',
    'reader':'',
    'uiEditable':Eds.Disabled,
    'uiVisible':True,
    'uiCategory':'01_General',
    'uiDecorated':True,
    }
),
)

DrcEntryProperties = (
('label',
    {
    'type':'drc_base',
    'isMulti':False,
    'accessor':'',
    'reader':'',
    'uiEditable':Eds.Disabled,
    'uiVisible':True,
    'uiDisplay':'Name',
    'uiCategory':'01_General',
    'uiDecorated':True,
    }
),
('name',
    {
    'type':'drc_base',
    'isMulti':False,
    'accessor':'_qfileinfo',
    'reader':'fileName()',
    'uiEditable':Eds.Disabled,
    'uiVisible':False,
    'uiCategory':'01_General',
    'uiDecorated':False,
    }
),
('modifTime',
    {
    'type':'drc_time',
    'isMulti':False,
    'accessor':'_qfileinfo',
    'reader':'lastModified()',
    'uiEditable':Eds.Disabled,
    'uiVisible':True,
    'uiDisplay':'Modif. Date',
    'uiCategory':'05_File',
    }
),
# ('creationTime',
#     {
#     'type':'drc_time',
#     'isMulti':False,
#     'accessor':'_qfileinfo',
#     'reader':'created()',
#     'uiEditable':Eds.Disabled,
#     'uiVisible':True,
#     'uiDisplay':'Creation Date',
#     'uiCategory':'01_General',
#     }
# ),
)

DrcFileProperties = [

('fileSize',
    {
    'type':'drc_size',
    'isMulti':False,
    'accessor':'_qfileinfo',
    'reader':'size()',
    'uiEditable':Eds.Disabled,
    'uiVisible':True,
    'uiDisplay':'Size',
    'uiCategory':'05_File',
    }
),
('currentVersion',
    {
    'type':'drc_base',
    'isMulti':False,
    'default':0,
#    'accessor':'_dbnode',
#    'reader':'getField(version)',
#    'writer':'setField(version)',
#    'lazy':True,
    'copyable':True,
    'uiEditable':Eds.Disabled,
    'uiVisible':True,
    'uiDisplay':'Version',
    'uiCategory':'04_Version',
    }
),
('lockOwner',
    {
    'type':'drc_base',
    'isMulti':False,
    'default':'',
    'accessor':'_lockobj',
    'reader':'owner()',
    'uiEditable':Eds.Disabled,
    'uiVisible':True,
    'uiDisplay':'Locked by',
    'uiCategory':'04_Version',
    }
),
('locked',
    {
    'type':'drc_base',
    'isMulti':False,
    'default':False,
    'accessor':'_lockobj',
    'reader':'is_locked()',
    'writer':'set_locked()',
    'uiEditable':Eds.Disabled,
    'uiVisible':False,
    'uiDisplay':'',
    'uiCategory':None,
    }
),
('comment',
    {
    'type':'db_str',
    'isMulti':False,
    'default':'',
    'accessor':'_dbnode',
    'reader':'getField(comment)',
    'writer':'setField(comment)',
    'lazy':True,
    'copyable':True,
    'uiEditable':Eds.Enabled,
    'uiVisible':True,
    'uiDisplay':'',
    'uiCategory':'04_Version',
    }
),
('checksum',
    {
    'type':'db_str',
    'isMulti':False,
    'default':'',
    'accessor':'_dbnode',
    'reader':'getField(checksum)',
    'writer':'setField(checksum)',
    'lazy':True,
    'copyable':True,
    'uiEditable':Eds.Disabled,
    'uiVisible':True,
    'uiDisplay':'',
    'uiCategory':None,
    }
),
('sourceFile',
    {
    'type':'db_str',
    'isMulti':False,
    'default':'',
    'accessor':'_dbnode',
    'reader':'getField(sourceFile)',
    'writer':'setField(sourceFile)',
    'lazy':True,
    'copyable':True,
    'uiEditable':Eds.Disabled,
    'uiVisible':True,
    'uiDisplay':'',
    'uiCategory':None,
    }
),
('author',
    {
    'type':'db_str',
    'isMulti':False,
    'default':'',
    'accessor':'_dbnode',
    'reader':'getField(author)',
    'writer':'',
    'lazy':True,
    'copyable':True,
    'uiEditable':Eds.Disabled,
    'uiVisible':True,
    'uiDisplay':'',
    'uiCategory':'04_Version',
    }
),
]
DrcFileProperties.extend(DrcEntryProperties)

class DrcBaseProperty(MetaProperty):

    def __init__(self, sProperty, metaobj):
        super(DrcBaseProperty, self).__init__(sProperty, metaobj)
        self.viewItems = []

    def iconSource(self):
        return self._metaobj.iconSource()

    def imageSource(self):
        return self._metaobj.imagePath()

class FileTimeProperty(DrcBaseProperty):

    def read(self):
        return DrcBaseProperty.read(self).toPython()


class FileSizeProperty(DrcBaseProperty):

    def read(self):
        return MemSize(DrcBaseProperty.read(self))


class DbStrProperty(DrcBaseProperty):

    def __init__(self, sProperty, metaobj):
        super(DrcBaseProperty, self).__init__(sProperty, metaobj)

    def createAccessor(self):
        return self._metaobj.createDbNode()


class PropertyFactory(BasePropertyFactory):

    propertyTypeDct = {
    'drc_base' : DrcBaseProperty,
    'drc_time' : FileTimeProperty,
    'drc_size' : FileSizeProperty,
    'db_str' : DbStrProperty,
    }


class DrcMetaObject(MetaObject):

    propertyFactoryClass = PropertyFactory
