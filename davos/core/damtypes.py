


class DamUser(object):

    def __init__(self, project, userData):

        self.loginName = userData["login"]
        self.name = userData.get("name", self.loginName)
