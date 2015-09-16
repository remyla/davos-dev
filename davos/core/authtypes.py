
import os
import  hashlib

from pytd.core.authenticator import Authenticator

from pytd.util.fsutils import jsonRead, jsonWrite
from pytd.util.fsutils import pathJoin
from pytd.util.sysutils import toStr
from pytd.util.logutils import logMsg



class HellAuth(Authenticator):

    def __init__(self):
        self.cookieFilePath = pathJoin(os.getenv("USERPROFILE"), "dev_auth.json")

    def loggedUser(self):

        if os.path.isfile(self.cookieFilePath):
            return jsonRead(self.cookieFilePath)

        return {}

    def logIn(self, sLogin, sPassword, **kwargs):
        userData = {"login":sLogin}
        jsonWrite(self.cookieFilePath, userData)
        return userData

    def logOut(self):
        if os.path.isfile(self.cookieFilePath):
            os.remove(self.cookieFilePath)


class ShotgunAuth(Authenticator):

    def __init__(self, project):
        super(ShotgunAuth, self).__init__()

        self._shotgundb = project._shotgundb
        assert self._shotgundb is not None, "No Shotgun instance found in {}".format(project)

    def loggedUser(self):
        userData = self._shotgundb.getLoggedUser()
        return userData

    def logIn(self, sLogin, sPassword, **kwargs):
        userData = self._shotgundb.loginUser(sLogin, sPassword, **kwargs)
        return userData

    def logOut(self):
        return self._shotgundb.logoutUser()


class DamasAuth(Authenticator):

    def __init__(self, project):
        super(DamasAuth, self).__init__()

        self._damasdb = project._damasdb
        assert self._damasdb is not None, u"No Damas instance found in {}".format(project)

        self.cookieFilePath = pathJoin(os.getenv("USERPROFILE"), "damas_auth.json")

    def loggedUser(self, *args, **kwargs):

        userData = None

        tokenData = self._readTokenData()
        if not tokenData:
            return None

        damasdb = self._damasdb
        damasdb.token = tokenData
        damasdb.headers['Authorization'] = 'Bearer ' + tokenData['token']

        if damasdb.verify():
            sLogin = tokenData["username"]
            userData = {"login":sLogin}
            print u"Damas successfully authenticated user: '{}' !".format(sLogin)

        return userData

    def logIn(self, sLogin, sPassword, **kwargs):

        userData = None

        if not self._damasdb.signIn(sLogin, sPassword):
            raise RuntimeError(u"Damas failed to authenticate user: '{}' !".format(sLogin))
        else:
            tokenData = self._damasdb.token

            sLogin = tokenData["username"]
            userData = {"login":sLogin}

            print u"Damas successfully authenticated user: '{}' !".format(sLogin)

            if kwargs.get("writeCookie", True):
                self._writeTokenData()

        return userData

    def logOut(self, *args, **kwargs):
        return self._damasdb.signOut()

    def _writeTokenData(self, tokenData):
        try:
            self.__writeTokenData(tokenData)
        except Exception, e:
            msg = (u"Could not write cookie file: '{}'!\n    {}"
                   .format(self.cookieFilePath, toStr(e)))
            logMsg(msg, warning=True)

    def __writeTokenData(self, tokenData):

        cookieData = {}
        sCookieFilePath = self.cookieFilePath
        if os.path.isfile(sCookieFilePath):
            cookieData = jsonRead(sCookieFilePath)

        sFieldList = ("username", "token_iat", "token_exp", "token")
        savedData = dict((f, tokenData[f]) for f in sFieldList)

        cookieData[self._hashedServerURL()] = savedData
        return jsonWrite(sCookieFilePath, cookieData)

    def _readTokenData(self):

        tokenData = {}
        sCookieFilePath = self.cookieFilePath

        if os.path.isfile(sCookieFilePath):
            cookieData = jsonRead(sCookieFilePath)
            tokenData = cookieData.get(self._hashedServerURL(), tokenData)

        return tokenData

    def _hashedServerURL(self):
        h = hashlib.sha1()
        h.update(self._damasdb.serverURL)
        return h.hexdigest()


class DualAuth(Authenticator):

    def __init__(self, project):
        self._shotgunAuth = ShotgunAuth(project)
        self._damasAuth = DamasAuth(project)

    def loggedUser(self):

        dmsUsrData = self._damasAuth.loggedUser()
        if not dmsUsrData:
            return None

        sgUsrData = self._shotgunAuth.loggedUser()
        if not sgUsrData:
            return None

        return sgUsrData

    def logIn(self, sLogin, sPassword):

        if not self._damasAuth.logIn(sLogin, sPassword, writeCookie=False):
            return None

        userData = self._shotgunAuth.logIn(sLogin, sPassword)
        if not userData:
            return None

        self._damasAuth._writeTokenData(self._damasAuth._damasdb.token)

        return userData

    def logOut(self):
        self._shotgunAuth.logOut()
        self._damasAuth.logOut()
