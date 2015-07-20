
import os.path as osp
from pytk.util.external.uicutils import compileUiDirToPyDir
import pytk.davos.gui.ui

compileUiDirToPyDir(osp.dirname(__file__), osp.dirname(pytk.davos.gui.ui.__file__))