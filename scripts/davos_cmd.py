
import argparse

import os
os.environ["PYTHONINSPECT"] = "1"

try:
    import davos_env
    davos_env.load()
except ImportError:pass

from davos.core.damproject import DamProject

parser = argparse.ArgumentParser()
parser.add_argument("--project", "-p", default=os.environ.get("DAVOS_INIT_PROJECT"))
ns = parser.parse_args()

sProject = ns.project
if not sProject:
    sProject = raw_input("project: ")

proj = DamProject(sProject)
while not proj:
    sProject = raw_input("project: ")
    proj = DamProject(sProject)

print ""
print (" Project: '{}' ".format(sProject)).center(80, "-")
