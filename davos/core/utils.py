
import re
import os

from pytd.gui.dialogs import promptDialog
from pytd.util.logutils import logMsg
from pytd.util.sysutils import importModule
from fnmatch import fnmatch
from pytd.util.fsutils import pathSplitDirs


_interDashesRgx = re.compile(r'-([a-z][0-9]+)')


def getConfigModule(sProjectName):

    try:
        sConfPkg = os.environ.get("DAVOS_CONF_PACKAGE", "davos.config")
        sConfigModule = sConfPkg + '.' + sProjectName
        modobj = importModule(sConfigModule)
    except ImportError:
        raise ImportError("No config module named '{}'".format(sConfigModule))

    return modobj

def versionFromName(sFileName):
    vers = findVersionFields(sFileName)
    return int(vers[0].strip('v')) if vers else None

def findVersionFields(s):
    return _interDashesRgx.findall(s)

def promptForComment(**kwargs):

    sComment = ""

    result = promptDialog(title='Please...',
                        message='Leave a comment: ',
                        button=['OK', 'Cancel'],
                        defaultButton='OK',
                        cancelButton='Cancel',
                        dismissString='Cancel',
                        scrollableField=True,
                        **kwargs)

    if result == 'Cancel':
        logMsg("Cancelled !" , warning=True)
    elif result == 'OK':
        sComment = promptDialog(query=True, text=True)

    return sComment

def projectNameFromPath(p):

    sConfPkg = os.environ.get("DAVOS_CONF_PACKAGE", "davos.config")
    pkg = importModule(sConfPkg)
    sPkgDirPath = os.path.dirname(pkg.__file__)

    sDirList = pathSplitDirs(p)

    for sFilename in os.listdir(sPkgDirPath):

        bIgnored = False
        for sPatrn in ("__*", ".*", "*.pyc"):
            if fnmatch(sFilename, sPatrn):
                bIgnored = True
                break

        if bIgnored:
            continue

        sModName = os.path.splitext(sFilename)[0]
        m = importModule(sConfPkg + '.' + sModName)

        sProjDir = m.project.dir_name
        if sProjDir in sDirList:
            return sModName

    return ""
