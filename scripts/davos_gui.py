
import argparse

import davos_env
davos_env.load()

from davos.tools import asset_browser

parser = argparse.ArgumentParser()
parser.add_argument("--project", "-p")
ns, args = parser.parse_known_args()

sProject = ns.project
if not sProject:
    sProject = raw_input("project: ")

asset_browser.launch(sProject, args)
