
import re

from pytk.core.dialogs import promptDialog
from pytk.util.logutils import logMsg
from pytk.util.sysutils import importModule


_interDashesRgx = re.compile(r'-([a-z][0-9]+)')


def getConfigModule(sProjectName):

    sConfigModule = sProjectName

    try:
        modobj = importModule(sConfigModule)
    except ImportError:
        sConfigModule = 'pytk.davos.config.' + sProjectName
        modobj = importModule(sConfigModule)

    reload(modobj)

    return modobj

def versionFromName(sFileName):
    vers = findVersionFields(sFileName)
    return int(vers[0].strip('v')) if vers else None

def findVersionFields(s):
    return _interDashesRgx.findall(s)

def promptForComment(**kwargs):

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
        return

    sComment = promptDialog(query=True, text=True)
    if not sComment:
        return

    return sComment
