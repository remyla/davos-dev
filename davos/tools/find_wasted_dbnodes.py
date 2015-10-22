
import os

from davos.core.damproject import DamProject
from pytd.util.sysutils import timer

def _iterWastedDbNodes(proj, dbNodeList):

    iNumNodes = len(dbNodeList)

    pubLibs = tuple(l for l in proj.loadedLibraries.itervalues() if l.isPublic())

    c = 0
    for dbnode in dbNodeList:
        c += 1
        print "Processing {}/{} db nodes...".format(c, iNumNodes)

        sDbPath = dbnode.file
        sAbsPath = ""
        for pubLib in pubLibs:
            try:
                sAbsPath = pubLib.dbToAbsPath(sDbPath)
            except ValueError:
                continue

            break

        if not sAbsPath:
            sAbsPath = sDbPath

        if not os.path.exists(sAbsPath):
            yield dbnode, sAbsPath

@timer
def findWastedDbNodes(*args):
    return tuple(_iterWastedDbNodes(*args))

def launch(bDryRun=True, project=""):

    sProject = os.environ["DAVOS_INIT_PROJECT"] if not project else project
    proj = DamProject(sProject)
    print sProject.center(80, "-")

    dbNodeList = proj.findDbNodes()

    wastedNodes = findWastedDbNodes(proj, dbNodeList)

    print '\n', '\n'.join(n.file + "\n    " + os.path.normpath(p) for n, p in wastedNodes)
    print "found {}/{} unused DbNodes".format(len(wastedNodes), len(dbNodeList))

    if not bDryRun:
        for n, _ in wastedNodes:
            print "deleting", n
            n.delete()
