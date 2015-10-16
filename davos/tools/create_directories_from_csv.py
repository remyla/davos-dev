
import sys
import os
osp = os.path
import csv

from PySide import QtGui

from pytd.util.sysutils import toStr
from davos.core.damtypes import DamAsset
from pytd.util.strutils import assertChars


def createAssetDirectories(proj, sCsvFilePath, **kwargs):

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

def launch(proj, dry_run=False):

    app = QtGui.qApp
    if not app:
        app = QtGui.QApplication(sys.argv)

    sCsvFilePath, _ = QtGui.QFileDialog.getOpenFileName(filter="*.csv")
    if sCsvFilePath:
        createAssetDirectories(proj, sCsvFilePath, dry_run=dry_run)

