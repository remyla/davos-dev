
import sys
import os
osp = os.path
import re

import csv
#import itertools as itl

from PySide import QtGui
from PySide.QtGui import QTreeWidgetItem, QTreeWidgetItemIterator
from PySide.QtCore import Qt

from pytd.util.fsutils import pathNorm, pathSplitDirs, pathJoin
from pytd.util.sysutils import toStr, qtGuiApp, argToTuple
from davos.core.damproject import DamProject
from davos.core.damtypes import DamAsset, DamShot
from pytd.util.strutils import assertChars
from pytd.gui.dialogs import SimpleTreeDialog, confirmDialog


class TreeItem(QTreeWidgetItem):

    def __init__(self, *args, **kwargs):
        super(TreeItem, self).__init__(*args, **kwargs)

        if kwargs.get("checkable", True):
            self.setFlags(self.flags() | Qt.ItemIsTristate)
            self.setCheckState(0, Qt.Checked)

def iterMissingPathItems(proj, sEntityType, sgEntityList):

    if sEntityType == "asset":
        entityCls = DamAsset
    elif sEntityType == "shot":
        entityCls = DamShot
    else:
        raise ValueError("Invalid entity type: '{}'.".format(sEntityType))

    for sgEntity in sgEntityList:

        sEntityName = sgEntity["code"]
        damEntity = None

        try:
            damEntity = entityCls(proj, name=sEntityName)
        except Exception, e:
            sError = toStr(e)
            print "'{}': {}.".format(sEntityName, sError)
            yield sEntityName, sError
        else:
            sMissingPaths = damEntity.createDirsAndFiles(dryRun=True, log=False)
            if not sMissingPaths:
                continue

            yield damEntity, sMissingPaths

def loadTreeItem(parent, sItemPath, sTextList, flags=None, userData=None, **kwargs):

    global TREE_ITEM_DCT

    item = TreeItem(parent, sTextList, **kwargs)
    TREE_ITEM_DCT[sItemPath] = item

    if flags is not None:
        item.setFlags(flags)

    if userData is not None:
        item.setData(0, Qt.UserRole, userData)

    return item

def launch(entityType="", dryRun=True, project=""):

    global TREE_ITEM_DCT
    TREE_ITEM_DCT = {}

    app = qtGuiApp()
    if not app:
        app = QtGui.QApplication(sys.argv)

    sProject = os.environ["DAVOS_INIT_PROJECT"] if not project else project
    proj = DamProject(sProject)
    print sProject.center(80, "-")

    shotgundb = proj._shotgundb
    sg = shotgundb.sg

    missingPathItems = []

    if not entityType:
        sEntityTypes = ("asset", "shot")
    else:
        sEntityTypes = argToTuple(entityType)

    bAssets = "asset" in sEntityTypes
    bShots = "shot" in sEntityTypes

    if bAssets:

        sSectionList = []
        confobj = proj._confobj
        for sSection, _ in confobj.listSections():
            if not confobj.getVar(sSection, "template_dir", ""):
                continue

            sSectionList.extend(confobj.getVar(sSection, "aliases", ()))

        filters = [["project", "is", {"type":"Project", "id":shotgundb._getProjectId()}],
                   ["sg_status_list", "is_not", "omt"],
                   ["sg_asset_type", "in", sSectionList]]

        allSgAstList = sg.find("Asset", filters, ["code", "sg_asset_type", "sg_status_list"],
                               [{'field_name':'sg_asset_type', 'direction':'asc'},
                                {'field_name':'code', 'direction':'asc'}])

        print "Assets:", len(allSgAstList)

    if bShots:

        filters = [["project", "is", {"type":"Project", "id":shotgundb._getProjectId()}],
                   ["sg_status_list", "is_not", "omt"],
                   ["sg_sequence", "is_not", None],
                   ["sg_sequence.Sequence.sg_status_list", "is_not", "omt"]
                   ]

        allSgShotList = sg.find("Shot", filters, ["code", "sg_sequence", "sg_status_list"],
                               [{'field_name':'sg_sequence', 'direction':'asc'},
                                {'field_name':'code', 'direction':'asc'}])

        print "Shots:", len(allSgShotList)

    if bAssets:
        missingPathItems = list(iterMissingPathItems(proj, "asset", allSgAstList))

    if bShots:
        missingPathItems.extend(iterMissingPathItems(proj, "shot", allSgShotList))

    dlg = SimpleTreeDialog()
    treeWdg = dlg.treeWidget
    treeWdg.setHeaderLabels(("Entity Name", "Infos"))

    badEntityItems = []
    for damEntity, sMissingPaths in missingPathItems:

        if isinstance(damEntity, basestring):
            badEntityItems.append((damEntity, sMissingPaths))
            continue

        drcLib = proj.getLibrary("public", damEntity.libraryName)
        sLibPath = drcLib.absPath()
        sEntityTitle = damEntity.sgEntityType + 's'

        sEntityPath = damEntity.getPath("public")
        sEntityPath = re.sub("^" + sLibPath, sEntityTitle, sEntityPath)
        sEntityPathDirs = pathSplitDirs(sEntityPath)

        for sAbsPath in sMissingPaths:

            sTreePath = re.sub("^" + sLibPath, sEntityTitle, sAbsPath)

            sParentPath, sFilename = osp.split(pathNorm(sTreePath))
            parentItem = TREE_ITEM_DCT.get(sParentPath)
            if not parentItem:
                sDirList = pathSplitDirs(sParentPath)
                curParentItem = treeWdg
                for i, sDirName in enumerate(sDirList):
                    if i == 0:
                        sItemPath = sDirName
                    else:
                        sItemPath = pathJoin(*sDirList[:i + 1])

                    item = TREE_ITEM_DCT.get(sItemPath)
                    if not item:
                        flags = None
                        if sItemPath.startswith(sEntityPath):
                            if len(pathSplitDirs(sItemPath)) > len(sEntityPathDirs):
                                flags = Qt.NoItemFlags

                        userData = None
                        if sItemPath == sEntityPath:
                            userData = damEntity

                        item = loadTreeItem(curParentItem, sItemPath, [sDirName],
                                            flags=flags, userData=userData)

                    curParentItem = item

                parentItem = curParentItem

            flags = None
            if sTreePath.startswith(sEntityPath):
                if len(pathSplitDirs(sTreePath)) > len(sEntityPathDirs):
                    flags = Qt.NoItemFlags

            userData = None
            if sTreePath == sEntityPath:
                userData = damEntity

            loadTreeItem(parentItem, sTreePath, [sFilename], flags=flags, userData=userData)


    if badEntityItems:

        errorsItem = loadTreeItem(None, "Errors", ["ERRORS"])
        treeWdg.insertTopLevelItem(0, errorsItem)

        for sEntityName, sError in badEntityItems:
            loadTreeItem(errorsItem, sEntityName, [sEntityName, sError],
                         checkable=False)

    for i in xrange(treeWdg.topLevelItemCount()):
        treeWdg.topLevelItem(i).setExpanded(True)

    while True:

        bOk = dlg.exec_()
        if not bOk:
            return

        bApply = False

        treeIter = QTreeWidgetItemIterator(treeWdg, QTreeWidgetItemIterator.Checked)
        damEntities = tuple(it.value().data(0, Qt.UserRole) for it in treeIter)
        damAssets = tuple(e for e in damEntities if isinstance(e, DamAsset))
        damShots = tuple(e for e in damEntities if isinstance(e, DamShot))
        if damAssets or damShots:

            sMsg = "Create directories and files for:\n"
            if damAssets:
                sMsg += "\n     - {} Assets".format(len(damAssets))

            if damShots:
                sMsg += "\n     - {} Shots".format(len(damShots))

            sConfirm = confirmDialog(title="WARNING !",
                                     message=sMsg,
                                     button=("Yes", "No"),
                                     defaultButton="No",
                                     cancelButton="No",
                                     dismissString="No",
                                     icon="warning",
                                    )

            if sConfirm == "Yes":
                bApply = True
                break

    if bApply:
        for damEntity in damEntities:
            if not damEntity:
                continue
            damEntity.createDirsAndFiles(dryRun=dryRun)

def createFromCsv(sEntityType, sCsvFilePath, project="", **kwargs):

    if sEntityType == "asset":
        sEntityFields = ("Asset Name", "asset name")
        entityCls = DamAsset
    elif sEntityType == "shot":
        sEntityFields = ("Shot Code", "shot code")
        entityCls = DamShot
    else:
        raise ValueError("Invalid entity type: '{}'".format(sEntityType))

    sProject = os.environ["DAVOS_INIT_PROJECT"] if not project else project
    proj = DamProject(sProject)
    print sProject.center(80, "-")

    iMaxCount = kwargs.get("maxCount", -1)

    with open(sCsvFilePath, 'rb') as csvFile:

        dialect = csv.Sniffer().sniff(csvFile.read(4096))
        csvFile.seek(0)

        reader = csv.reader(csvFile, dialect)

        iNameColumn = -1
        iHeaderRow = 0

        for row in reader:

            bFound = False
            for sField in sEntityFields:
                try:
                    iNameColumn = row.index(sField)
                except ValueError:
                    pass
                else:
                    bFound = True
                    break

            if bFound:
                break

            iHeaderRow += 1

        assert iNameColumn != -1, 'Asset names missing from "{}" !'.format(sCsvFilePath)

        csvFile.seek(0)
        for _ in xrange(iHeaderRow + 1):
            reader.next()

        sEntityList = []
        damEntityList = []
        sErrorList = []
        for row in reader:

            sEntityName = row[iNameColumn]
            if sEntityName in sEntityList:
                continue

            sEntityList.append(sEntityName)

            try:
                assertChars(sEntityName, r'[\w]')
            except AssertionError, e1:
                sErrorList.append(toStr(e1))
                continue

            try:
                damEntity = entityCls(proj, name=sEntityName)
            except Exception, e2:
                sErrorList.append(toStr(e2))
                continue

            print sEntityName
            damEntityList.append(damEntity)

        if sErrorList:
            raise RuntimeError("\n".join(sErrorList))

    count = 0
    for damEntity in damEntityList:

        if count == iMaxCount:
            break

        if damEntity.createDirsAndFiles(**kwargs):
            count += 1

    sCreated = "will create" if kwargs.get("dryRun") else "created"
    print "{} asset directories {}.".format(count, sCreated)
