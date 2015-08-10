
import os

from pytd.util.logutils import logMsg

from pytd.util.external.lockfile import LockError, UnlockError
#from pytd.util.external.lockfile import LockBase
from pytd.util.external.lockfile.mkdirlockfile import MkdirLockFile


class LockFile(MkdirLockFile):

    def __init__(self, path, sUserLogin):

        self.path = path
        root, tail = os.path.split(path)
        self.lock_file = os.path.join(os.path.abspath(root), "." + tail) + ".lock"
        self.unique_name = os.path.join(self.lock_file, sUserLogin)
        self.timeout = -1

    def owner(self):
        logMsg(log='all')

        if not self.is_locked():
            return ""

        files = os.listdir(self.lock_file)
        return files[0] if files else ""

    def setLocked(self, bLock):

        if bLock:
            try:self.acquire()
            except LockError:return False
        else:
            try:self.release()
            except UnlockError:return False

        return True

    def isLocked(self):
        return self.is_locked()


    def breakLock(self):
        return self.break_lock()