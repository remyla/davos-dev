
import os.path as osp
from pytd.util.external.uicutils import compileUiDirToPyDir
import davos.gui.ui

compileUiDirToPyDir(osp.dirname(__file__), osp.dirname(davos.gui.ui.__file__))