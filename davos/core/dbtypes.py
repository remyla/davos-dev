
import os

from pytd.util.logutils import logMsg#, forceLog
#from pytd.util.sysutils import timer
#from pytd.util.sysutils import toStr

class DummyDbCon(object):

    def create(self, keys):
        logMsg(u"{}({})".format('dry-run: create', keys), log='debug')
        return {}

    def update(self, id_, keys):
        logMsg(u"{}({})".format('dry-run: update', id_, keys), log='debug')
        return []

    def delete(self, id_) :
        logMsg(u"{}({})".format('dry-run: delete', id_), log='debug')
        return True

    def search(self, sQuery):
        logMsg(u"{}({})".format('dry-run: search', sQuery), log='debug')
        return []

    def read(self, ids):
        logMsg(u"{}({})".format('dry-run: read', ids), log='debug')
        return []


class DrcDb(object):

    def __init__(self, dbcon, sUserLogin):
        self._dbcon = dbcon
        self.userLogin = sUserLogin

    def createNode(self, data):

        rec = self._dbcon.create(data)
        if rec is None:
            raise DbCreateError("Failed to create node: {}".format(data))

        #TODO:remove return type when fixed by remy
        #r = rec[0] if isinstance(rec, (list, tuple, set)) else rec

        return DbNode(self, rec)

    def findOne(self, sQuery):

        ids = self._dbcon.search(sQuery)
        if not ids:
            return None

        if len(ids) > 1:
            raise ValueError("Several nodes found: {}".format(ids))
        else:
            nodeId = ids[0]
            recs = self.read(nodeId)
            return DbNode(self, recs[0])

    def findNodes(self, sQuery, asDict=False, keyField=""):
        logMsg(sQuery, log='all')

        nodesIter = self._iterNodes(sQuery)

        if asDict:
            if not keyField:
                raise ValueError("To be able to return as dict, \
                                please provide a 'keyField'!")

            return dict((n.getField(keyField), n) for n in nodesIter) if nodesIter else {}

        return list(nodesIter) if nodesIter else []

    def _iterNodes(self, sQuery):
        logMsg(sQuery, log='all')

        ids = self.search(sQuery)
        if not ids:
            return None

        return (DbNode(self, r) for r in self.read(ids))

    def readNodes(self, ids):
        return list(DbNode(self, r) for r in self.read(ids))

    def search(self, sQuery):
        logMsg(sQuery, log='all')

        ids = self._dbcon.search(sQuery)
        if ids is None:
            raise DbSearchError('Failed to search: "{}"'
                                .format(sQuery))

        return ids

    def read(self, ids):

        if isinstance(ids, basestring):
            sIds = ids
        else:
            sIds = ",".join(ids)

        recs = self._dbcon.read(sIds)
        if recs is None:
            raise DbReadError('Failed to read ids: \n\n{}'.format(sIds))

        return recs


class DbNode(object):

    __slots__ = ('__drcdb', '_dbcon', '_data', 'id_', '__dirty', 'name')

    def __init__(self, drcdb, record=None):

        self.__drcdb = drcdb
        self._dbcon = drcdb._dbcon
        self.id_ = ''
        self._data = None
        self.__dirty = False
        self.name = ''

        if record is not None:
            self.loadData(record)

    def loadData(self, data):

        if not isinstance(data, dict):
            raise TypeError("argument 'data' must be a {}. Got {}."
                            .format(dict, type(data)))
#        elif not data:
#            raise ValueError("Invalid value passed to argument 'data': {}"
#                             .format(data))

        self.id_ = data.pop('_id', self.id_)
        self._data = data.copy()
        self.__dirty = False

        self.name = os.path.basename(data.get('file', ''))

    def isDirty(self):
        return self.__dirty

    def getField(self, sField):
        return self._data.get(sField, "")

    def setField(self, sField, value, useCache=False):

        if useCache:
            self._data[sField] = value
            self.__dirty = True
        else:
            recs = self._dbcon.update(self.id_, {sField:value})
            if not recs:
                #raise DbUpdateError("Failed to update {}".format(self))
                return False

            self.loadData(recs[0])

        return True

    def hasField(self, sField):
        return sField in self._data

    def setData(self, data):

        recs = self._dbcon.update(self.id_, data)
        if not recs:
#            raise DbUpdateError("Failed to update {}".format(self))
            return False

        self.loadData(recs[0])

        return True

    def setLocked(self, bLock):

        if bLock:
            sUserLogin = self.__drcdb.userLogin
            if not sUserLogin:
                raise ValueError("Invalid user login: '{}'".format(sUserLogin))

            bSuccess = self.setField("lock", sUserLogin)
        else:
            bSuccess = self.setField("lock", None)

        return bSuccess

    def isLocked(self):
        return True if self.owner() else False

    def owner(self):
        return self.getField("lock")

    #@forceLog(log='debug')
    def refresh(self, data=None):
        logMsg(log='all')

        if data is None:

            if self.__dirty:
                recs = self._dbcon.update(self.id_, self._data)
                if not recs:
                    raise DbUpdateError("Failed to update {}: \n{}".format(self, self.dataRepr()))
                logMsg(u"Refeshing from DB update: {}.".format(self), log='debug')
            else:
                recs = self._dbcon.read(self.id_)
                if not recs:
                    raise DbReadError("Failed to read {}".format(self))
                logMsg(u"Refeshing from DB read: {}.".format(self), log='debug')

            newData = recs[0]

        else:
            logMsg(u"Refeshing from input data: {}.".format(self), log='debug')
            newData = data

        self.loadData(newData)

    def delete(self):
        return self._dbcon.delete(self.id_)

    def logData(self, *fields):
        print self.dataRepr(*fields)

    def dataRepr(self, *fields):
        bFilter = True if fields else False
        s = u'{'
        for k, v in sorted(self._data.iteritems(), key=lambda x:x[0]):
            if bFilter and k not in fields:
                continue
            s += u"\n'{}':'{}'".format(k, v)
        return (s + u'\n}')

    def __getattr__(self, name):

        sAccessor = '_data'

        if (name == sAccessor) and not hasattr(self, sAccessor):
            s = "'{}' object has no attribute '{}'.".format(type(self).__name__, name)
            raise AttributeError(s)

        value = self._data.get(name, "")
        return value


    def __repr__(self):

        cls = self.__class__

        try:
            sRepr = ("{}('{}')".format(cls.__name__, getattr(self, "name", self.id_)))
        except AttributeError:
            sRepr = cls.__name__

        return sRepr


class DbError(Exception):
    pass

class DbFieldError(DbError):
    pass

class DbReadError(DbError):
    pass

class DbUpdateError(DbError):
    pass

class DbSearchError(DbError):
    pass

class DbDeleteError(DbError):
    pass

class DbCreateError(DbError):
    pass
