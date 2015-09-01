
import os
import argparse

try:
    import davos_env
    davos_env.load()
except ImportError:pass

from davos.tools import file_browser

parser = argparse.ArgumentParser()
parser.add_argument("--project", "-p", default=os.environ.get("DAVOS_INIT_PROJECT"))
ns, args = parser.parse_known_args()

sProject = ns.project
if not sProject:
    sProject = raw_input("project: ")

file_browser.launch(sProject, args)
