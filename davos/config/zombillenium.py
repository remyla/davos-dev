

class project:

#    dir_name = "zombillenium"
    maya_version = 2016

    #public_path = '//Diskstation/z2k/05_3D/{}/'.format(dir_name)
    private_path = '${ZOMBI_PRIVATE_PATH}/'
    damas_root_path = "zomb/"

    template_path = '${ZOMBI_TOOL_PATH}/template/'

    libraries = (
        "asset_lib",
        "shot_lib",
        "output_lib",
        )

    authenticator = ".authtypes.ShotgunAuth"
    #no_damas = True


class asset_lib:

    public_path = '${ZOMBI_ASSET_DIR}'#project.public_path + dir_name
    private_path = project.private_path + "asset"

    asset_types = ("chr", "env", "prp")

    asset_tree = {
        "{assetType}":
            {
            "{asset} -> asset_dir":
                {
                "texture -> texture_dir":{},
                "ref -> ref_dir":{},
                "image -> image_dir":{},
                "{asset}_master.ma -> master_scene":{},
                "{asset}_previz.ma -> previz_scene":{},
                "{asset}_preview.jpg -> preview_image":{},
                },
            },
        }


class shot_lib:

    public_path = '${ZOMBI_SHOT_DIR}'#project.public_path + dir_name
    private_path = project.private_path + "shot"

    shot_tree = {
        "{sequence}":
            {
            "{shot} -> shot_dir":
                {
                 "01_previz@step":
                    {
                     "{shot}_previz.ma -> previz_scene":{},
                     "{shot}_previz.mov -> previz_capture":{},
                    },
                },
            },
        }

    all_resources = {
    "previz_scene":{"produces":["previz_capture", ] },
    "previz_capture":{},
                     }


class output_lib:

    public_path = '${ZOMBI_OUTPUT_DIR}'#project.public_path + dir_name
    private_path = project.private_path + "output"




