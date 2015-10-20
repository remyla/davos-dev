
import sys
import os
osp = os.path
import csv
#import itertools as itl

from PySide import QtGui
from PySide.QtGui import QTreeWidget, QTreeWidgetItem
from PySide.QtCore import Qt

from pytd.util.sysutils import toStr, qtGuiApp
from davos.core.damproject import DamProject
from davos.core.damtypes import DamAsset
from pytd.util.strutils import assertChars

def createFromCsv(proj, sCsvFilePath, **kwargs):

    iMaxCount = kwargs.get("maxCount", -1)

    with open(sCsvFilePath, 'rb') as csvFile:

        dialect = csv.Sniffer().sniff(csvFile.read(4096))
        csvFile.seek(0)

        reader = csv.reader(csvFile, dialect)

        iNameColumn = -1
        iHeaderRow = 0

        for row in reader:

            bFound = False
            for sAstNameField in ("Asset Name", "asset name"):
                try:
                    iNameColumn = row.index(sAstNameField)
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

        sAstNameList = []
        damAstList = []
        sErrorList = []
        for row in reader:

            sAstName = row[iNameColumn]
            if sAstName in sAstNameList:
                continue

            sAstNameList.append(sAstName)

            try:
                assertChars(sAstName, r'[\w]')
            except AssertionError, e1:
                sErrorList.append(toStr(e1))
                continue

            try:
                damAst = DamAsset(proj, name=sAstName)
            except Exception, e2:
                sErrorList.append(toStr(e2))
                continue

            print sAstName
            damAstList.append(damAst)

        if sErrorList:
            raise RuntimeError("\n".join(sErrorList))


    count = 0
    for damAst in damAstList:

        if count == iMaxCount:
            break

        if damAst.createDirsAndFiles(**kwargs):
            count += 1

    sCreated = "will be created" if kwargs.get("dry_run") else "created"
    print "{} asset directories {}.".format(count, sCreated)

class TreeItem(QTreeWidgetItem):

    def __init__(self, *args, **kwargs):
        super(TreeItem, self).__init__(*args, **kwargs)

        self.setFlags(self.flags() | Qt.ItemIsTristate)
        self.setCheckState(0, Qt.Checked)

def launch(dry_run=True):

    app = qtGuiApp()
    if not app:
        app = QtGui.QApplication(sys.argv)

    sProject = os.environ["DAVOS_INIT_PROJECT"]
    proj = DamProject(sProject)
    print sProject.center(80, "-")

    shotgundb = proj._shotgundb
    sg = shotgundb.sg

    sSectionList = []
    confobj = proj._confobj
    for sSection, _ in confobj.listSections():
        if not confobj.getVar(sSection, "template_dir", ""):
            continue

        sSectionList.extend(confobj.getVar(sSection, "aliases", ()))

    print sSectionList

    filters = [["project", "is", {"type":"Project", "id":shotgundb._getProjectId()}],
               ["sg_status_list", "is_not", "omt"],
               ["sg_asset_type", "in", sSectionList]]

    allSgAstList = sg.find("Asset", filters, ["code", "sg_asset_type", "sg_status_list"],
                           [{'field_name':'sg_asset_type', 'direction':'asc'},
                            {'field_name':'code', 'direction':'asc'}])

    print len(allSgAstList)

    treeWdg = QTreeWidget()

    topLevelItemDct = {}
    for sgAst in allSgAstList:

        sAstType = sgAst["sg_asset_type"]
        sAstName = sgAst["code"]

        try:
            damAst = DamAsset(proj, name=sAstName)
        except Exception, e:
            print "Failed loading asset: '{}'. {}.".format(sAstName, toStr(e))

        sMissingPath = damAst.createDirsAndFiles(dry_run=True)
        if not sMissingPath:
            continue

        if sAstType not in topLevelItemDct:
            topItem = TreeItem(treeWdg, [sAstType])
            topLevelItemDct[sAstType] = topItem
        else:
            topItem = topLevelItemDct[sAstType]

        TreeItem(topItem, [sAstName])

    treeWdg.show()
    sys.exit(app.exec_())

launch()
