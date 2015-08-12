
from . import zombillenium as zombase

class project(zombase.project):

    dir_name = "zombdev"

    public_path = '//Diskstation/Projects/{}/'.format(dir_name)
    private_path = '//Diskstation/Projects/private/${{DAM_USER}}/{}/'.format(dir_name)
    damas_root_path = "zomb/"
    template_path = '${ZOMBI_TOOL_PATH}/template/'

class asset_lib(zombase.asset_lib):

    dir_name = "asset"

    public_path = project.public_path + dir_name
    private_path = project.private_path + dir_name


class shot_lib(zombase.shot_lib):

    dir_name = "shot"

    public_path = project.public_path + dir_name
    private_path = project.private_path + dir_name


class output_lib(zombase.output_lib):

    dir_name = "output"

    public_path = project.public_path + dir_name
    private_path = project.private_path + dir_name




