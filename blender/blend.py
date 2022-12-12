import sys

import bpy
import os
import glob
from typing import Optional
import addon_utils
from argparse import ArgumentParser


def build(args):
    if not os.path.isdir(args.input_directory):
        raise RuntimeError(f'{args.input_directory} is not a directory')

    package_name = os.path.basename(args.input_directory)
    class_type = 'StaticMesh'

    # TODO: not ideal, filter this out before we get here!
    count = 0

    for file in glob.glob('**StaticMesh/*.psk*', root_dir=args.input_directory):
        filename = os.path.join(args.input_directory, file)

        try:
            bpy.ops.import_scene.psk(filepath=filename, should_import_skeleton=False, should_import_materials=False)
        except Exception as e:
            print(e)
            continue

        object_name = os.path.splitext(os.path.basename(file))[0]

        new_object = bpy.data.objects[object_name]
        new_object.data['bdk_package_reference'] = f'{class_type}\'{package_name}.{object_name}\''
        new_object.asset_mark()
        # new_object.asset_generate_preview(use_background_thread=False)   # 3.5 only
        new_object.asset_generate_preview()

        count += 1

    if args.output_path is None:
        args.output_path = os.path.join(args.input_directory, f'{package_name}.blend')

    output_directory = os.path.dirname(args.output_path)

    print('OD')
    print(output_directory)

    os.makedirs(output_directory, exist_ok=True)

    if count > 0:
        bpy.ops.wm.save_as_mainfile(
            filepath=os.path.abspath(args.output_path),
            copy=True
            )


if __name__ == '__main__':
    addon_utils.enable('io_scene_psk_psa')

    parser = ArgumentParser()
    subparsers = parser.add_subparsers(title='command')
    build_subparser = subparsers.add_parser('build')
    build_subparser.add_argument('input_directory')
    build_subparser.add_argument('--output_path', required=False, default=None)
    build_subparser.set_defaults(func=build)
    args = sys.argv[sys.argv.index('--')+1:]
    args = parser.parse_args(args)
    print(args.input_directory)
    args.func(args)
