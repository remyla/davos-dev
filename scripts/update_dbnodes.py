
import os
from davos.core.damproject import DamProject

from pytd.util.fsutils import iterPaths, ignorePatterns

sProject = os.environ["DAVOS_INIT_PROJECT"]

proj = DamProject(sProject)

print sProject.center(80, "-")

def launch(bDryRun=True):

    dbNodeDct = dict((n.file, n)  for n in proj.findDbNodes())

    for drcLib in proj.loadedLibraries.itervalues():

        if not drcLib.isPublic():
            continue

        for p in iterPaths(drcLib.absPath(), dirs=False,
                           ignoreDirs=ignorePatterns(".*", "chr_old", "*xxxx*")):

            entry = drcLib.getEntry(p, dbNode=False)
            if not entry:
                print "No such", p
                continue

            sDbPath = entry.damasPath().lower()
            dbnode = dbNodeDct.get(sDbPath)
            if not dbnode:
                continue

            print dbnode
            sNewDbPath = "/" + entry.damasPath()
    #        print sNewDbPath
    #        print dbnode.file

            data = {"file":sNewDbPath}
            if not dbnode.checksum:
                print "empty checksum found"
                data["checksum"] = None

            if bDryRun:
                print data
            else:
                dbnode.setData(data)
                dbnode.logData()

            print ""