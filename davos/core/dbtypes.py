
import os

from pytd.util.logutils import logMsg#, forceLog
from pytd.util.sysutils import chunkate, toStr
#from pytd.util.sysutils import toStr

class DummyDbCon(object):

    def create(self, keys):
        logMsg(u"{}({})".format('dummy: create', keys), log='debug')
        return {}

    def update(self, id_, keys):
        logMsg(u"{}({})".format('dummy: update', id_, keys), log='debug')
        return []

    def delete(self, id_) :
        logMsg(u"{}({})".format('dummy: delete', id_), log='debug')
        return True

    def search(self, sQuery):
        logMsg(u"{}({})".format('dummy: search', sQuery), log='debug')
        return []

    def read(self, ids):
        logMsg(u"{}({})".format('dummy: read', ids), log='debug')
        return []


class DrcDb(object):

    def __init__(self, project):

        if project._damasdb is None:
            raise AssertionError(u"No Damas instance found in {}".format(project))

        if project._authobj is None:
            raise AssertionError(u"No Authenticator instance found in {}"
                                 .format(project))

        self.project = project
        self._dbconn = project._damasdb

    @property
    def userLogin(self):
        damUser = self.project.loggedUser()
        return damUser.loginName if damUser else ""

    def createNode(self, data):

        rec = self._dbconn.create(data)
        if rec is None:
            raise DbCreateError("Failed to create node: {}".format(data))

        return DbNode(self, rec)

    def findOne(self, sQuery):

        ids = self._search(sQuery)#self._dbconn.search(sQuery)
        if not ids:
            return None

        if len(ids) > 1:
            for n in self.nodeForIds(ids):
                n.logData()
            raise ValueError("Several nodes found for '{}'.".format(sQuery))
        else:
            nodeId = ids[0]
            recs = self._read(nodeId)
            return DbNode(self, recs[0])

    def findNodes(self, sQuery, **kwargs):
        logMsg(sQuery, log='all')

        nodesIter = self._iterNodes(sQuery)

        bDict = kwargs.get("asDict", False)
        sKeyField = kwargs.get("keyField", "")

        if bDict:
            if not sKeyField:
                raise ValueError("To be able to return as dict, \
                                please provide a 'keyField'!")

            return dict((n.getField(sKeyField), n) for n in nodesIter) if nodesIter else {}

        nodes = list(nodesIter) if nodesIter else []
        return nodes

    def _iterNodes(self, sQuery):
        logMsg(sQuery, log='all')

        ids = self._search(sQuery)
        if not ids:
            return None

        return (DbNode(self, r) for r in self._read(ids) if r is not None)

    def nodeForIds(self, ids):
        return list(DbNode(self, r) for r in self._read(ids) if r is not None)

    def updateNodes(self, nodes, data):

        ids = tuple(n.id_ for n in nodes)
        recs = self._update(ids, data)

#        print len(nodes), len(recs)
#        for node, rec in zip(nodes, recs):
#            print node.id_, rec["_id"]
#        print "------", set(n.id_ for n in nodes) - set(r["_id"] for r in recs)

        for node, rec in zip(nodes, recs):

            if node.id_ != rec["_id"]:
                msg = (" Ids mismatch between {} and update record id: {} != {} !"
                        .format(node, node.id_, rec["_id"]))
                raise ValueError(msg)

            node.loadData(rec)

    def _search(self, sQuery, authOnFail=True):
        logMsg(sQuery, log='all')

        dbconn = self._dbconn

        ids = dbconn.search(sQuery)
        if ids is None:

            if not authOnFail:
                raise DbSearchError('Failed to search: "{}"'.format(sQuery))

            bAuthOk = dbconn.verify()
            if not bAuthOk:
                try:
                    bAuthOk = self.project.authenticate()
                except Exception, e:
                    logMsg(toStr(e), warning=True)

            return self._search(sQuery, authOnFail=False)

        return ids

    def _read(self, ids):

        numIds = len(ids)
        if numIds > 3260:#TODO: remove when ids limit fixed in Damas
            #print numIds
            recs = []
            dbcon = self._dbconn
            for chunkIt in chunkate(ids, 3260):
                subIds = tuple(chunkIt)
                #print len(subIds)
                recs.extend(dbcon.read(subIds))
        else:
            recs = self._dbconn.read(ids)
            if recs is None:
                raise DbReadError('Failed to read ids: \n\n{}'.format(ids))

        return recs

    def _update(self, ids, data):

        recs = self._dbconn.update(ids, data)
        if recs is None:
            raise DbUpdateError('Failed to update ids: \n\n{}'.format(ids))

        return recs

    def createVersion(self, id_, data):

        rec = self._dbconn.version(id_, data)
        if rec is None:
            raise DbCreateError("Failed to version node: {}".format(data))

        return DbNode(self, rec)

class DbNode(object):

    __slots__ = ('__drcdb', '_dbconn', '_data', 'id_', '__dirty', 'name')

    def __init__(self, drcdb, record=None):

        self.__drcdb = drcdb
        self._dbconn = drcdb._dbconn
        self.id_ = ''
        self._data = None
        self.__dirty = False
        self.name = ''

        if record is not None:
            self.loadData(record)

    def loadData(self, in_data):

        if not isinstance(in_data, dict):
            raise TypeError("argument 'data' must be a {}. Got {}."
                            .format(dict, type(in_data)))
#        elif not data:
#            raise ValueError("Invalid value passed to argument 'data': {}"
#                             .format(data))
        data = in_data.copy()

        self.id_ = data.pop('_id', self.id_)
        self._data = data
        self.__dirty = False

        p = data.get('file', '')
        if p.endswith("/"):
            p = p[:-1]

        self.name = os.path.basename(p)

    def isDirty(self):
        return self.__dirty

    def getField(self, sField):
        return self._data.get(sField, "")

    def setField(self, sField, value, useCache=False):

        if useCache:
            self._data[sField] = value
            self.__dirty = True
        else:
            recs = self._dbconn.update(self.id_, {sField:value})
            if not recs:
                #raise DbUpdateError("Failed to update {}".format(self))
                return False

            self.loadData(recs[0])

        return True

    def hasField(self, sField):
        return sField in self._data

    def getData(self, *fields):

        if fields:
            data = dict((f, v) for f, v in self._data.iteritems() if f in fields)
        else:
            data = self._data.copy()

        return data

    def setData(self, data):

        recs = self._dbconn.update(self.id_, data)
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
                recs = self._dbconn.update(self.id_, self._data)
                if not recs:
                    raise DbUpdateError("Failed to update {}: \n{}".format(self, self.dataRepr()))
                logMsg(u"Refeshing from DB update: {}.".format(self), log='debug')
            else:
                recs = self._dbconn.read(self.id_)
                if not recs:
                    raise DbReadError("Failed to read {}".format(self))
                logMsg(u"Refeshing from DB read: {}.".format(self), log='debug')

            newData = recs[0]

        else:
            logMsg(u"Refeshing from input data: {}.".format(self), log='debug')
            newData = data

        self.loadData(newData)

    def delete(self):
        return self._dbconn.delete(self.id_)

    def logData(self, *fields):
        print self.dataRepr(*fields)

    def dataRepr(self, *fields):
        bFilter = True if fields else False
        s = u'{'
        for k, v in sorted(self._data.iteritems(), key=lambda x:x[0]):
            if bFilter and (k not in fields):
                continue
            s += u"\n{}: {} | {}".format(k, v, type(v))
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
            sRepr = ("{}({})".format(cls.__name__, getattr(self, "name", self.id_)))
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
