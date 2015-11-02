
import os
import argparse

from davos.core.damproject import DamProject
from davos.core.damtypes import DamAsset, DamShot

def run():

    parser = argparse.ArgumentParser()
    parser.add_argument("projectName")
    parser.add_argument("dependencyType")
    parser.add_argument("entityType")
    parser.add_argument("entityName")
    parser.add_argument("listingFile")
    parser.add_argument("comment")
    parser.add_argument("--dryRun", type=int, default=1)

    ns = parser.parse_args()

    proj = DamProject(ns.projectName)

    sEntityType = ns.entityType

    if sEntityType == "asset":
        EntityCls = DamAsset
    elif sEntityType == "shot":
        EntityCls = DamShot
    else:
        raise ValueError("Invalid entity type: '{}'.".format(sEntityType))

    damEntity = EntityCls(proj, name=ns.entityName)

    sListFilePath = ns.listingFile
    if not os.path.isfile(sListFilePath):
        raise ValueError("No such file: '{}'".format(sListFilePath))

    sDepFileList = []
    sNotFoundFileList = []
    with open(sListFilePath, 'r') as listingFile:
        for p in listingFile:
            p = p.strip()
            if os.path.isfile(p):
                sDepFileList.append(p)
            else:
                sNotFoundFileList.append(p)

    if sNotFoundFileList:
        sMsg = "No such files:\n    "
        sMsg += "\n    ".join(sNotFoundFileList)
        raise AssertionError(sMsg)

    if not sDepFileList:
        raise AssertionError("No files listed in '{}'".format(sListFilePath))

    sDepType = ns.dependencyType
    sComment = ns.comment
    bDryRun = ns.dryRun
    print proj, damEntity, sDepType, sComment, bDryRun

    proj.publishDependencies(sDepType, damEntity, sDepFileList, sComment, dryRun=bDryRun)

    os.remove(sListFilePath)

if __name__ == "__main__":

    os.environ["PYTHONINSPECT"] = "1"
    try:
        run()
    except:
        os.environ["PYTHONINSPECT"] = "1"
        raise

