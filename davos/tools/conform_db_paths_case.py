
import os
from davos.core.damproject import DamProject

from pytd.util.fsutils import iterPaths, ignorePatterns

sProject = os.environ["DAVOS_INIT_PROJECT"]

proj = DamProject(sProject)

print sProject.center(80, "-")

def launch(bDryRun=True):

    dbNodeDct = dict((n.file.lower(), n)  for n in proj.findDbNodes())

    for drcLib in proj.loadedLibraries.itervalues():

        if not drcLib.isPublic():
            continue

        for p in iterPaths(drcLib.absPath(), dirs=True,
                           ignoreDirs=ignorePatterns(".*", "chr_old", "*xxxx*"),
                           ignoreFiles=ignorePatterns(".*", "Thumbs.db", "*xxxx*")):

            entry = drcLib.getEntry(p, dbNode=False)
            if not entry:
                print "No such", p
                continue

            sDbPath = entry.dbPath().lower()
            dbnode = dbNodeDct.get(sDbPath)
            if not dbnode:
                continue

            sDbFilePath = entry.dbPath()
            sDbNodePath = dbnode.file
            if sDbNodePath != sDbFilePath:
                print "\nfs:", sDbFilePath, "\ndb:", sDbNodePath
                if not bDryRun:
                    dbnode.setField("file", sDbFilePath)
                    print dbnode.dataRepr("file")
