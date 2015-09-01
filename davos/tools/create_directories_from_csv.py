
import sys
import os
import re
import csv

from PySide import QtGui

from pytd.util.sysutils import toStr
from davos.core.damtypes import DamAsset

osp = os.path

def assertStr(sWord, sRegexp, **kwargs):

    sErrorMsg = ""

    sInvalidChars = re.sub(sRegexp, "", sWord)
    if sInvalidChars:

        sInvalidChars = ", ".join("'{0}'".format(toStr(c)) for c in set(sInvalidChars))
        sErrorMsg += ('\t- contains invalid characters: {0}\n\n'
                      .format(sInvalidChars.replace("' '", "'space'")))

    if sErrorMsg:
        sErrorMsg = 'Invalid string: "{0}"\n'.format(toStr(sWord)) + sErrorMsg
        raise AssertionError, sErrorMsg

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
        sErrorList = []
        for row in reader:
            sAstName = row[iNameColumn]
            try:
                assertStr(sAstName, r'[\w]')
            except AssertionError, e:
                sErrorList.append(toStr(e))
                continue

            sAstNameList.append(sAstName)

        if sErrorList:
            raise AssertionError, "".join(sErrorList)

        count = 0
        for sAstName in sAstNameList:

            if count == iMaxCount:
                break

            damAst = DamAsset(proj, name=sAstName)
            damAst.createDirsAndFiles(**kwargs)

            count += 1

def launch(proj, dry_run=False):

    app = QtGui.qApp
    if not app:
        app = QtGui.QApplication(sys.argv)

    sCsvFilePath, _ = QtGui.QFileDialog.getOpenFileName(filter="*.csv")
    if sCsvFilePath:
        createAssetDirectories(proj, sCsvFilePath, dry_run=dry_run)

