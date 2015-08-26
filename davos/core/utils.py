
import re
import os

from pytd.gui.dialogs import promptDialog
from pytd.util.logutils import logMsg
from pytd.util.sysutils import importModule


_interDashesRgx = re.compile(r'-([a-z][0-9]+)')


def getConfigModule(sProjectName):

    try:
        sConfPkg = os.environ.get("DAVOS_CONF_PACKAGE", "")
        if sConfPkg:

            sConfigModule = sConfPkg + '.' + sProjectName
            modobj = importModule(sConfigModule)

        else:
            sConfigModule = 'davos.config.' + sProjectName
            modobj = importModule(sConfigModule)

    except ImportError:
        raise ImportError("No config module named '{}'".format(sConfigModule))

    reload(modobj)

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

    if not sComment:
        raise RuntimeError, "Comment has NOT been provided !"

    return sComment
