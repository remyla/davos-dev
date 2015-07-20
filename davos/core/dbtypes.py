from pytd.util.logutils import logMsg, forceLog
from pytd.util.sysutils import toStr

class DrcDb(object):

    def __init__(self, dbcon):
        self._dbcon = dbcon

    def createNode(self, data):

        rec = self._dbcon.create(data)
        if rec is None:
            raise DbCreateError("Failed to create node: {}".format(data))

        return DbNode(self._dbcon, rec)

    def findOne(self, sQuery):

        ids = self._dbcon.search(sQuery)
        if not ids:
            return None

        if len(ids) > 1:
            raise ValueError("Several nodes found: {}".format(ids))
        else:
            nodeId = ids[0]
            recs = self.read(nodeId)
            return DbNode(self._dbcon, recs[0])

    def findNodes(self, sQuery, asDict=False, keyField=""):

        nodesIter = self._iterNodes(sQuery)

        if asDict:
            if not keyField:
                raise ValueError("To be able to return as dict, please provide a 'keyField'!")

            return dict((n.getValue(keyField), n) for n in nodesIter) if nodesIter else {}

        return list(self._iterNodes(sQuery)) if nodesIter else []

    def _iterNodes(self, sQuery):

        ids = self.search(sQuery)
        if not ids:
            return None

        return (DbNode(self._dbcon, r) for r in self.read(ids))

    def search(self, sQuery):
        ids = self._dbcon.search(sQuery)
        if ids is None:
            raise DbSearchError('Failed to search: "{}"'
                                .format(sQuery))

        return ids

    def read(self, ids):

        if isinstance(ids, basestring):
            s = ids
        else:
            s = ",".join(ids)

        recs = self._dbcon.read(s)
        if recs is None:
            raise DbReadError('Failed to read ids: \n\n{}'.format(s))

        return recs


class DbNode(object):

    __slots__ = ('_dbcon', '_data', 'id_', '__dirty')

    def __init__(self, dbcon, record=None):

        self._dbcon = dbcon
        self.id_ = ''
        self._data = None
        self.__dirty = False

        if record is not None:
            self.loadData(record)

    def loadData(self, data):

        if not isinstance(data, dict):
            raise TypeError("argument 'data' must be a {}. Got {}."
                            .format(dict, type(data)))
        elif not data:
            raise ValueError("Invalid value passed to argument 'data': {}"
                             .format(data))

        self.id_ = data.pop('_id', self.id_)
        self._data = data.copy()
        self.__dirty = False

    def isDirty(self):
        return self.__dirty

    def getValue(self, sField):
        return self._data.get(sField, "")

    def setValue(self, sField, value, cached=False):

        if cached:
            self._data[sField] = value
            self.__dirty = True
        else:
            recs = self._dbcon.update(self.id_, {sField:value})
            if not recs:
                #raise DbUpdateError("Failed to update {}".format(self))
                return False

            self.loadData(recs[0])

        return True

    def setData(self, data):

        recs = self._dbcon.update(self.id_, data)
        if not recs:
#            raise DbUpdateError("Failed to update {}".format(self))
            return False

        self.loadData(recs[0])

        return True

    @forceLog(log='debug')
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

    def logData(self):
        print self.dataRepr()

    def dataRepr(self):
        s = '{'
        for k, v in sorted(self._data.iteritems(), key=lambda x:x[0]):
            s += "\n'{}':'{}'".format(k, toStr(v))
        return s + '\n}'

#    def __getattr__(self, name):
#
#        sAccessor = '_data'
#
#        if (name == sAccessor) and not hasattr(self, sAccessor):
#            s = "'{}' object has no attribute '{}'.".format(type(self).__name__, name)
#            raise AttributeError(s)
#
#        value = self._data.get(name, "")
#        return value


    def __repr__(self):

        cls = self.__class__

        try:
            sRepr = ("{}('{}')".format(cls.__name__, self._data.get("name", self.id_)))
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
