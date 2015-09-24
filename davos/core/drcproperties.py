
from datetime import datetime

from pytd.util.utiltypes import MemSize

from pytd.core.metaproperty import BasePropertyFactory
from pytd.core.metaproperty import MetaProperty
from pytd.core.metaproperty import EditState as Eds
from pytd.core.metaobject import MetaObject
from pytd.util.sysutils import toTimestamp, argToList, inDevMode

def syncProperty(sDbKey, **kwargs):
    params = {
    'type':'db_sync',
    'isMulti':False,
    'default':0,
    'accessor':'_dbnode',
    'reader':'getField({})'.format(sDbKey),
    'writer':'setField({})'.format(sDbKey),
    'lazy':True,
    'copyable':True,
    'uiEditable':Eds.Enabled if inDevMode() else Eds.Disabled,
    'uiVisible':True,
    'uiCategory':"06_Sync",
    }
    params.update(**kwargs)
    return params

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
('fsMtime',
    {
    'type':'drc_time',
    'isMulti':False,
    'default':0,
    'accessor':'_qfileinfo',
    'reader':'lastModified()',
    'uiEditable':Eds.Disabled,
    'uiVisible':True,
    'uiDisplay':'Modif. Date',
    'uiCategory':None,
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
('syncRules',
    {
    'type':'db_str',
    'isMulti':True,
    'default':[],
    'accessor':'_dbnode',
    'reader':'getField(sync_rules)',
    'writer':'setField(sync_rules)',
    'lazy':True,
    'copyable':True,
    'uiEditable':Eds.Enabled if inDevMode() else Eds.Disabled,
    'uiVisible':True,
    'uiDisplay':'',
    'uiCategory':"06_Sync",
    }
),
('onlineSync',
    syncProperty("online", uiDisplay="Online")
),
('dmnParisSync',
    syncProperty("dmn_paris", uiDisplay="Paris")
),
('dmnAngoulmSync',
    syncProperty("dmn_angouleme", uiDisplay="Angouleme")
),
('dreamWallSync',
    syncProperty("dream_wall", uiDisplay="DreamWall")
),
('pipangaiSync',
    syncProperty("pipangai", uiDisplay="Pipangai")
),
)

DrcFileProperties = [

('fileSize',
    {
    'type':'drc_size',
    'isMulti':False,
    'default':0,
    'accessor':'_qfileinfo',
    'reader':'size()',
    'uiEditable':Eds.Disabled,
    'uiVisible':True,
    'uiDisplay':'Size',
    'uiCategory':'05_File',
    }
),
('lockOwner',
    {
    'type':'db_str',
    'isMulti':False,
    'default':'',
    'accessor':'_dbnode',
    'reader':'owner()',
    'lazy':True,
    'uiEditable':Eds.Disabled,
    'uiVisible':True,
    'uiDisplay':'Locked by',
    'uiCategory':'04_Version',
    }
),
('currentVersion',
    {
    'type':'db_int',
    'isMulti':False,
    'default':0,
    'accessor':'_dbnode',
    'reader':'getField(version)',
    'writer':'setField(version)',
    'lazy':True,
    'copyable':True,
    'uiEditable':Eds.Disabled,
    'uiVisible':True,
    'uiDisplay':'Version',
    'uiCategory':'04_Version',
    }
),
('dbMtime',
    {
    'type':'db_time',
    'isMulti':False,
    'default':0,
    'accessor':'_dbnode',
    'reader':'getField(time)',
    'writer':'setField(time)',
    'lazy':True,
    'copyable':True,
    'uiEditable':Eds.Disabled,
    'uiVisible':True,
    'uiDisplay':'Version Date',
    'uiCategory':'04_Version',
    }
),
('locked',
    {
    'type':'db_str',
    'isMulti':False,
    'default':False,
    'accessor':'_dbnode',
    'reader':'isLocked()',
    'writer':'setLocked()',
    'lazy':True,
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
('author',
    {
    'type':'db_str',
    'isMulti':False,
    'default':'',
    'accessor':'_dbnode',
    'reader':'getField(author)',
    'writer':'setField(author)',
    'lazy':True,
    'copyable':True,
    'uiEditable':Eds.Disabled,
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

class DrcSizeProperty(DrcBaseProperty):

    def read(self):
        return MemSize(DrcBaseProperty.read(self))

class DrcTimeProperty(DrcBaseProperty):

    def read(self):
        value = DrcBaseProperty.read(self)
        if type(value).__name__ == "QDateTime":
            return value.toPython()
        elif value:
            return datetime.fromtimestamp(value)


class DbStrProperty(DrcBaseProperty):

    def __init__(self, sProperty, metaobj):
        super(DbStrProperty, self).__init__(sProperty, metaobj)

    def read(self):
        value = DrcBaseProperty.read(self)
        if self.isMulti():
            return value.split(u',') if value else []
        return value

    def castToWrite(self, in_value):
        value = DrcBaseProperty.castToWrite(self, in_value)

        if self.isMulti():
            if value and isinstance(value, basestring):
                values = self._splitRgx.findall(value)
            else:
                values = argToList(value)

            value = u",".join(values) if value else None

        return value

    def createAccessor(self):
        dbnode = self._metaobj.getDbNode()
        if not dbnode:
            dbnode, _ = self._metaobj.createDbNode(check=False)
        return dbnode

class DbIntProperty(DbStrProperty):

    def __init__(self, sProperty, metaobj):
        super(DbIntProperty, self).__init__(sProperty, metaobj)

    def read(self):
        value = DbStrProperty.read(self)
        if isinstance(value, basestring):
            return int(value) if value else 0
        return value

    def castToWrite(self, in_value):
        value = DbStrProperty.castToWrite(self, in_value)
        return int(value) if value else 0

class DbBoolProperty(DbIntProperty):

    def __init__(self, sProperty, metaobj):
        super(DbBoolProperty, self).__init__(sProperty, metaobj)

    def read(self):
        return bool(DbIntProperty.read(self))

class DbSyncProperty(DbBoolProperty):

    def __init__(self, sProperty, metaobj):
        super(DbSyncProperty, self).__init__(sProperty, metaobj)

#    def read(self):
#        value = DbBoolProperty.read(self)
#        return bool(value) if value else False

    def castToWrite(self, in_value):
        value = DbBoolProperty.castToWrite(self, in_value)
        return value if value else None

class DbTimeProperty(DbIntProperty):

    timeZone = "local"

    def read(self):
        timestamp = DbIntProperty.read(self)
        if not timestamp:
            return None

        # MongoDb timestamps are expressed in milliseconds.
        if self.__class__.timeZone == "utc":
            dateTime = datetime.utcfromtimestamp(timestamp * 0.001)
        else:
            dateTime = datetime.fromtimestamp(timestamp * 0.001)

        return dateTime

    def castToWrite(self, in_value):

        if isinstance(in_value, datetime):

            value = toTimestamp(in_value, self.__class__.timeZone)

        elif isinstance(in_value, (int, long)):

            if not in_value:
                raise ValueError("Bad value for {}.{}: {}."
                       .format(self._metaobj, self.name, in_value))

            try:
                datetime.fromtimestamp(in_value)
            except:
                raise
            else:
                value = in_value
        else:
            sAllowedTypes = tuple(t.__name__ for t in(datetime, int, long))
            raise TypeError("Got {} for {}.{}. Expected {}"
                            .format(type(in_value), self._metaobj, self.name,
                                    sAllowedTypes))

        # MongoDb timestamps are expressed in milliseconds.
        return value * 1000


class PropertyFactory(BasePropertyFactory):

    propertyTypeDct = {
    'drc_base' : DrcBaseProperty,
    'drc_size' : DrcSizeProperty,
    'drc_time' : DrcTimeProperty,
    'db_str' : DbStrProperty,
    'db_int' : DbIntProperty,
    'db_sync': DbSyncProperty,
    'db_time' : DbTimeProperty,
    }

class DrcMetaObject(MetaObject):

    propertyFactoryClass = PropertyFactory
