
import os

from davos.core.damproject import DamProject
from pytd.util.sysutils import timer

def _iterWastedDbNodes(proj, dbNodeList, limit=0):

    iNumNodes = len(dbNodeList)

    pubLibs = tuple(l for l in proj.loadedLibraries.itervalues() if l.isPublic())

    c = 0
    for dbnode in dbNodeList:
        c += 1

        if limit and c == limit:
            break

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
def findWastedDbNodes(*args, **kwargs):
    return tuple(_iterWastedDbNodes(*args, **kwargs))

proj = None
wastedNodes = None
dbNodeList = None

def launch(bDryRun=True, project="", **kwargs):

    global proj, wastedNodes, dbNodeList

    sProject = os.environ["DAVOS_INIT_PROJECT"] if not project else project
    proj = DamProject(sProject)
    print sProject.center(80, "-")

    if wastedNodes is None:
        dbNodeList = proj.findDbNodes()
        wastedNodes = findWastedDbNodes(proj, dbNodeList, **kwargs)

    numNodes = len(wastedNodes)
    print '\n', '\n'.join(n.file + "\n    " + os.path.normpath(p) for n, p in wastedNodes)
    print "found {}/{} unused DbNodes".format(numNodes, len(dbNodeList))

    if (not bDryRun) and numNodes:
        if raw_input("Delete these nodes ? (yes/no)").strip() == "yes":
            for n, _ in wastedNodes:
                print "deleting", n
                n.delete()
