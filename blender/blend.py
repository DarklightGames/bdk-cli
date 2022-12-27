import sys
from pathlib import Path

import bpy
import os
import glob
import addon_utils
from argparse import ArgumentParser

material_class_names = [
    'Combiner',
    'ConstantColor',
    'Cubemap',
    'FinalBlend',
    'Shader',
    'TexCoordSource',
    'TexOscillator',
    'TexPanner',
    'TexScaler',
    'TexRotator',
    'Texture',
    'TexEnvMap',
    'VertexColor'
]


def build(args):
    if not os.path.isdir(args.input_directory):
        raise RuntimeError(f'{args.input_directory} is not a directory')

    input_directory = Path(args.input_directory).resolve()

    package_name = input_directory.parts[-1]
    did_import_objects = False

    for file in glob.glob('**/*.props.txt', root_dir=args.input_directory):
        path = Path(os.path.join(args.input_directory, file))
        class_type = os.path.basename(path.parent)
        object_name = os.path.basename(file).replace('.props.txt', '')
        new_object = None

        if class_type == 'StaticMesh':
            extensions = ['.pskx', '.psk']
            filenames = [os.path.join(args.input_directory, 'StaticMesh', f'{object_name}{extension}') for extension in extensions]

            for filename in filenames:
                if os.path.isfile(filename):
                    print('found a file')
                    try:
                        bpy.ops.import_scene.psk(filepath=filename, should_import_skeleton=False,
                                                 should_import_materials=False)
                        print('imported', filename)
                    except Exception as e:
                        print(e)
                        continue
                    new_object = bpy.data.objects[object_name]
                    new_object.data['bdk_reference'] = f'{class_type}\'{package_name}.{object_name}\''
                    new_object.data.use_auto_smooth = False
                    did_import_objects = True
                    break
        elif class_type in material_class_names:
            filepath = os.path.join(args.input_directory, file)

            try:
                bpy.ops.import_material.umaterial(filepath=filepath)
            except Exception as e:
                print(e)
                continue
            new_object = bpy.data.materials[object_name]
            new_object['bdk_reference'] = f'{class_type}\'{package_name}.{object_name}\''
            did_import_objects = True

        if new_object is not None:
            new_object.asset_mark()
            new_object.asset_generate_preview(use_background_thread=False)  # 3.5 only

    if args.output_path is None:
        args.output_path = os.path.join(args.input_directory, f'{package_name}.blend')

    output_directory = os.path.join(os.path.dirname(args.output_path))
    os.makedirs(output_directory, exist_ok=True)

    if did_import_objects:
        bpy.ops.wm.save_as_mainfile(
            filepath=os.path.abspath(args.output_path),
            copy=True
            )


if __name__ == '__main__':
    addon_utils.enable('io_scene_psk_psa')
    addon_utils.enable('io_import_umaterial')

    parser = ArgumentParser()
    subparsers = parser.add_subparsers(title='command')
    build_subparser = subparsers.add_parser('build')
    build_subparser.add_argument('input_directory')
    build_subparser.add_argument('--output_path', required=False, default=None)
    build_subparser.set_defaults(func=build)
    args = sys.argv[sys.argv.index('--')+1:]
    args = parser.parse_args(args)
    args.func(args)
