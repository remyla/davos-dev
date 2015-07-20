import os

from pytd.core.authenticator import Authenticator

from pytd.util.fsutils import jsonRead, jsonWrite
from pytd.util.fsutils import pathJoin

class HellAuth(Authenticator):

    def __init__(self):
        self.authenticated = False
        self.cookieFile = pathJoin(os.getenv("USERPROFILE"),
                                   "dev_auth.json")

    def loggedUser(self, *args, **kwargs):

        if os.path.isfile(self.cookieFile):
            return jsonRead(self.cookieFile)

        return {}

    def logIn(self, sLogin, sPwd, **kwargs):
        userData = {"login":sLogin}
        jsonWrite(self.cookieFile, userData)
        return userData

    def logOut(self, *args, **kwargs):
        if os.path.isfile(self.cookieFile):
            os.remove(self.cookieFile)


class ShotgunAuth(Authenticator):

    def __init__(self, project):
        super(ShotgunAuth, self).__init__()
        self._shotgundb = project._shotgundb

        assert self._shotgundb is not None, "No Shotgun instance found in {}".format(project)

    def loggedUser(self, *args, **kwargs):
        userData = self._shotgundb.getLoggedUser(*args, **kwargs)
        return userData

    def logIn(self, *args, **kwargs):
        userData = self._shotgundb.loginUser(*args, **kwargs)
        return userData

    def logOut(self, *args, **kwargs):
        self._shotgundb.logoutUser(*args, **kwargs)


