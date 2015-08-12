import os.path as osp


class project:

    maya_version = 2016

    #public_path = '//Diskstation/z2k/05_3D/{}/'.format(dir_name)
    private_path = '$ZOMBI_PRIVATE_PATH/'
    damas_root_path = "zomb/"

    template_path = '$ZOMBI_TOOL_PATH/template/'

    libraries = (
        "asset_lib",
        "shot_lib",
        "output_lib",
        )

    child_sections = libraries

    authenticator = ".authtypes.ShotgunAuth"
    #no_damas = True

class asset_lib:

    public_path = '$ZOMBI_ASSET_DIR'
    private_path = project.private_path + "asset"

    asset_types = (
        "character3d",
        "prop3d",
        "vehicle3d",
        "set3d",
        "environment3d",
        )

    child_sections = asset_types

    asset_dir = "{asset_type}/{asset}"

class camera:

    prefix = "cam"
    asset_type = prefix

    public_path = osp.join(asset_lib.public_path, asset_lib.asset_dir)
    private_path = osp.join(asset_lib.private_path, asset_lib.asset_dir)

    resource_tree = {
        "{asset}.ma -> scene":None,
        }

class character3d:

    aliases = ("Character 3D",)
    prefix = "chr"
    asset_type = prefix

    public_path = osp.join(asset_lib.public_path, asset_lib.asset_dir)
    private_path = osp.join(asset_lib.private_path, asset_lib.asset_dir)

    template_path = osp.join(project.template_path, "asset_chr")

    resource_tree = {
        "ref -> ref_dir":{},
        "review -> review_dir":{},
        "script -> script_dir":{},
        "texture -> texture_dir":{},
        "{asset}_anim.ma -> anim_scene":None,
        "{asset}_modeling.ma -> modeling_scene":None,
        "{asset}_previz.ma -> previz_scene":None,
        "{asset}_render.ma -> render_scene":None,
        }

class prop3d:

    aliases = ("Prop 3D",)
    prefix = "prp"
    asset_type = prefix

    public_path = osp.join(asset_lib.public_path, asset_lib.asset_dir)
    private_path = osp.join(asset_lib.private_path, asset_lib.asset_dir)

    template_path = osp.join(project.template_path, "asset_vhlPrp")

    resource_tree = {
        "ref -> ref_dir":{},
        "review -> review_dir":{},
        #"script -> script_dir":{},
        "texture -> texture_dir":{},
        "{asset}_anim.ma -> anim_scene":None,
        "{asset}_modeling.ma -> modeling_scene":None,
        "{asset}_previz.ma -> previz_scene":None,
        "{asset}_render.ma -> render_scene":None,
        }

class vehicle3d(prop3d):

    aliases = ("Vehicle 3D",)
    prefix = "vhl"
    asset_type = prefix

class set3d:

    aliases = ("Set 3D",)
    prefix = "set"
    asset_type = prefix

    public_path = osp.join(asset_lib.public_path, asset_lib.asset_dir)
    private_path = osp.join(asset_lib.private_path, asset_lib.asset_dir)

    template_path = osp.join(project.template_path, "asset_envSet")

    resource_tree = {
        "ref -> ref_dir":{},
        "review -> review_dir":{},
        #"script -> script_dir":{},
        "texture -> texture_dir":{},
        "{asset}_previz.ma -> previz_scene":None,
        "{asset}_master.ma -> master_scene":None,
        }

class environment3d(set3d):

    aliases = ("Env 3D",)
    prefix = "env"
    asset_type = prefix

class shot_lib:

    public_path = '$ZOMBI_SHOT_DIR'
    private_path = project.private_path + "shot"

    shot_tree = {
        "{sequence}":
            {
            "{shot} -> shot_dir":
                {
                 "{step} -> step_dir":
                    {
                     "{shot}_previz.ma -> previz_scene":{},
                     "{shot}_previz.mov -> previz_capture":{},
                    },
                },
            },
        }

    resource_files = {
    "previz_scene":{"produces":["previz_capture", ] },
    "previz_capture":{},
    }

class output_lib:

    public_path = '$ZOMBI_OUTPUT_DIR'
    private_path = project.private_path + "output"




