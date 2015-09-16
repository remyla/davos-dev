

import os
from davos.core.damproject import DamProject
from pytd.util.sysutils import fromUtf8

#from pytd.util.fsutils import iterPaths, ignorePatterns

sProject = os.environ["DAVOS_INIT_PROJECT"]

proj = DamProject(sProject)

print sProject.center(80, "-")

def launch(dryRun=True):

    sg = proj._shotgundb.sg
    sgOperatorList = sg.find("CustomNonProjectEntity01", [],
                             fields=["sg_login", "sg_password", "sg_company"])

    dbUserList = proj._db.findNodes("username:/.*/")
    dbUserDict = dict((u.username, u) for u in dbUserList)

    for sgOp in sgOperatorList:

        sSgLogin, sSgPwd = sgOp["sg_login"], sgOp["sg_password"]
        sCompany = sgOp["sg_company"]["name"]
        #print sSgLogin, sSgPwd, toStr(sCompany)
        if not sSgPwd:
            continue

        sgData = {
                "username":sSgLogin,
                "password": sSgPwd,
                "company":fromUtf8(sCompany),
                }

        if sSgLogin in dbUserDict:

            userNode = dbUserDict[sSgLogin]
            updData = dict((k, v) for k, v in sgData.iteritems()
                                    if v != userNode.getField(k))

#            updData = {}
#            for k, v in sgData.iteritems():
#                print k, repr(v), repr(userNode.getField(k))

            #print userNode._data
            if updData:
                print "update user:", sSgLogin, updData
                if not dryRun:
                    print userNode.setData(updData)

        else:
            print "create user:", sgData
            if not dryRun:
                print proj._db.createNode(sgData)



#print proj._db.findNodes("username:sebastienc")
#print proj._damasdb.signIn("devzombi", "Zomb1llen1um")


