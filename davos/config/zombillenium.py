
class project:

    dir_name = "zombillenium"
    maya_version = 2016

    public_path = '//Diskstation/z2k/05_3D/{}/'.format(dir_name)
    private_path = '${{USERPROFILE}}/cg_projects/{}/'.format(dir_name)
    damas_path = "zomb/"

    template_path = '//Diskstation/z2k/05_3D/{}/tool/template/'.format(dir_name)

    libraries = (
        "asset_lib",
        "shot_lib",
        "output_lib",
        )

    authenticator = ".authtypes.ShotgunAuth"
    #no_damas = True

class asset_lib:

    dir_name = "asset"

    public_path = project.public_path + dir_name
    private_path = project.private_path + dir_name


    asset_tree = {
        "{assetType}":
            {
            "{asset} -> asset_dir":
                {
                "texture -> texture_dir":{},
                "ref -> ref_dir":{},
                "image -> image_dir":{},
                "{asset}_master.ma -> master_file":{},
                "{asset}_previz.ma -> previz_file":{},
                "{asset}_preview.jpg -> preview_file":{},
                },
            },
        }


class shot_lib:

    dir_name = "shot"

    public_path = project.public_path + dir_name
    private_path = project.private_path + dir_name


    shot_tree = {
        "{sequence}":
            {
            "{shot} -> shot_dir":
                {
                },
            },
        }

class output_lib:

    dir_name = "output"

    public_path = project.public_path + dir_name
    private_path = project.private_path + dir_name




