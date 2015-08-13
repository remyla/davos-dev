
import os
import sys
from pytd.util.fsutils import pathJoin, copyFile

sys.path.append(r'C:\Users\sebcourtois\devspace\git\z2k-pipeline-toolkit\launchers\paris')
import setup_env_tools
setup_env_tools.loadEnviron()

from davos.core.damproject import DamProject
#from davos.core.dbtypes import DummyDbCon, DrcDb

proj = DamProject("zombdev")

sMaFilePath = pathJoin(proj.getPath("template", "project"), "initial_files", "maya_2016.ma")
print sMaFilePath, os.path.isfile(sMaFilePath)

for sAstType in proj.getVar("asset_lib", "asset_types"):
    for sPathVar in proj.getVar(sAstType, "all_path_vars"):
        p = proj.getPath("template", sAstType, sPathVar)
        if p.endswith(".ma"):
            copyFile(sMaFilePath, p, dry_run=False)
