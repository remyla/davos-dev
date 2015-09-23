
import os
from datetime import datetime

from davos.core.damproject import DamProject
from davos.core.utils import versionFromName

sProject = os.environ["DAVOS_INIT_PROJECT"]

proj = DamProject(sProject)

print sProject.center(80, "-")

def launch(bDryRun=True):

    dbNodeDct = {}

    for n in proj.findDbNodes():
        dbNodeDct.setdefault(n.file, []).append(n)

#    st = datetime(2015, 9, 21)
#    et = datetime(2015, 9, 22)

    toDeleteNodes = []

    for nodes in dbNodeDct.itervalues():
        x = len(nodes)
        if x > 1:
            nodes = sorted(nodes, key=lambda x:int(x.time) * .001, reverse=True)
            print nodes
            for n in nodes:
                drcEntry = proj.entryFromDbNode(n, dbNode=False)
                v = versionFromName(drcEntry.name)
                if v is None:
                    v = drcEntry.latestBackupVersion()

                dt = datetime.fromtimestamp(int(n.time) * 0.001)
                #if dt >= st and dt < et:
                print "    {} {} {} {}".format(dt, v, n._data, n.id_)

                if n.version >= v:
                    toDeleteNodes.append(n)

    if not bDryRun:
        for n in toDeleteNodes:
            print "deleting", n
            n.delete()