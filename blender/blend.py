import sys

import bpy
import os
import glob
from typing import Optional
import addon_utils
from argparse import ArgumentParser


def build(input_directory: str, output_path: Optional[str]):
    if not os.path.isdir(input_directory):
        raise RuntimeError(f'{input_directory} is not a directory')

    package_name = os.path.basename(input_directory)
    class_type = 'StaticMesh'

    for file in glob.glob('**/*.psk*', root_dir=input_directory):
        filename = os.path.join(input_directory, file)

        try:
            bpy.ops.import_scene.psk(filepath=filename, should_import_skeleton=False, should_import_materials=False)
        except Exception as e:
            continue

        object_name = os.path.splitext(os.path.basename(file))[0]

        new_object = bpy.data.objects[object_name]
        new_object.data['u_package_reference'] = f'{class_type}\'{package_name}.{object_name}\''
        new_object.asset_mark()
        # new_object.asset_generate_preview(use_background_thread=False)   # 3.5 only
        new_object.asset_generate_preview()

    if output_path is None:
        output_path = os.path.join(input_directory, f'{package_name}.blend')

    bpy.ops.wm.save_as_mainfile(
        filepath=os.path.abspath(output_path),
        copy=True
        )


if __name__ == '__main__':
    addon_utils.enable('io_scene_psk_psa')

    parser = ArgumentParser()
    subparsers = parser.add_subparsers('command')
    build_subparser = subparsers.add_parser('build')
    build_subparser.add_argument('input_directory')
    build_subparser.add_argument('output_path', required=False, default=None)
    args = sys.argv[sys.argv.index('--')+1:]
    args = parser.parse_args(args)
    args.func(args)
