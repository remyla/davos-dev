
import os

from davos.core.damproject import DamProject

sProject = os.environ["DAVOS_INIT_PROJECT"]
proj = DamProject(sProject)
print sProject.center(80, "-")

def launch(bDryRun=True):

    unusedNodes = []

    projDbNodes = proj.findDbNodes()
    for dbnode in projDbNodes:
        if not proj.entryFromDbNode(dbnode):
            unusedNodes.append(dbnode)
            print dbnode.dataRepr('file').strip("{}").strip()

    print "found {}/{} unused DbNodes".format(len(unusedNodes), len(projDbNodes))

    if not bDryRun:
        for n in unusedNodes:
            print "deleting", n
            n.delete()