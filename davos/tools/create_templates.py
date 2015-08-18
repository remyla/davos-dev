
import os

from pytd.util.fsutils import pathJoin, copyFile

from davos.core.damproject import DamProject
#from davos.core.dbtypes import DummyDbCon, DrcDb

proj = DamProject("zombtest")

sMaFilePath = pathJoin(proj.getPath("template", "project"), "initial_files", "maya_2016.ma")
print sMaFilePath, os.path.isfile(sMaFilePath)

for sAstType in proj.getVar("asset_lib", "asset_types"):
    for sPathVar in proj.getVar(sAstType, "all_tree_vars"):
        p = proj.getTemplatePath(sAstType, sPathVar)
        if p.endswith(".ma"):
            copyFile(sMaFilePath, p, dry_run=False)
