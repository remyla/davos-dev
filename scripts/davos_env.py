

def load():
    try:
        import davos
    except ImportError:

        import os.path as osp
        import sys

        sDirName = "davos-dev"
        sCurDirPath, _ = osp.split(osp.abspath(__file__))
        sDavosRepoPath = osp.join(sCurDirPath.split(sDirName)[0], sDirName)

        print "PYTHONPATH += '{}'".format(sDavosRepoPath)
        sys.path.append(sDavosRepoPath)

    try:
        import pytd
    except ImportError:
        sPytdRepoPath = osp.join(osp.dirname(sDavosRepoPath), "pypeline-tool-devkit")
        if not osp.isdir(sPytdRepoPath):
            raise

        print "PYTHONPATH += '{}'".format(sPytdRepoPath)
        sys.path.append(sPytdRepoPath)
