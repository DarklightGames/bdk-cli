import argparse
import os
import re
import subprocess
from argparse import ArgumentParser
from glob import glob
from typing import Optional

from dotenv import load_dotenv
from tqdm import tqdm

BLENDER_VERSION_MIN = '3.4.0'
UMODEL_VERSION_MIN = 1590
IO_SCENE_PSK_PSA_VERSION_MIN = '4.2.0'
IO_IMPORT_UMATERIAL_VERSION_MIN = '0.1.0'

load_dotenv()


class UReference:
    type_name: str
    package_name: str
    group_name: Optional[str]
    object_name: str

    def __init__(self, type_name: str, package_name: str, object_name: str, group_name: Optional[str] = None):
        self.type_name = type_name
        self.package_name = package_name
        self.object_name = object_name
        self.group_name = group_name

    @staticmethod
    def from_string(string: str) -> Optional['UReference']:
        if string == 'None':
            return None
        pattern = r'(\w+)\'([\w\.\d\-\_]+)\''
        match = re.match(pattern, string)
        type_name = match.group(1)
        object_name = match.group(2)
        pattern = r'([\w\d\-\_]+)'
        values = re.findall(pattern, object_name)
        package_name = values[0]
        object_name = values[-1]
        return UReference(type_name, package_name, object_name, group_name=None)

    def __repr__(self):
        s = f'{self.type_name}\'{self.package_name}'
        if self.group_name:
            s += f'.{self.group_name}'
        s += f'.{self.object_name}'
        return s


def env(args: argparse.Namespace):
    # test that config is legit
    from env import test_environment
    test_environment(verbose=args.verbose)


def build(args: argparse.Namespace):
    from build import build_assets
    build_assets(dry=args.dry, mod=args.mod, clean=args.clean)


def export(args: argparse.Namespace):
    from build import export_assets
    export_assets(dry=args.dry, mod=args.mod, clean=args.clean)


def dirty(args: argparse.Namespace):
    from build import dirty_package
    dirty_package(args.package)


# TODO: messy as hell, this should maybe just be in the import material addon?
def build_cubemaps(args: argparse.Namespace):
    print('Scanning for cubemap files...')
    pattern = '**/Cubemap/*.props.txt'
    root_dir = os.path.abspath(os.environ['BUILD_DIR'])
    cubemap_files = []
    for file in glob(pattern, root_dir=root_dir, recursive=True):
        cubemap_files.append(file)
    print(f'Found {len(cubemap_files)} cubemap files')
    with tqdm(total=len(cubemap_files)) as pbar:
        for cubemap_file in cubemap_files:
            with open(os.path.join(os.environ['BUILD_DIR'], cubemap_file), 'r') as f:
                contents = f.read()
                textures = re.findall(r'Faces\[\d] = ([\w\d]+\'[\w\d_\-.]+\')', contents)
                faces = []
                for texture in textures:
                    face_reference = UReference.from_string(texture)
                    image_path = os.path.join(root_dir, face_reference.package_name, face_reference.type_name, f'{face_reference.object_name}.tga')
                    faces.append(image_path)
                # front, back, right, left, top, bottom
                output_path = os.path.join(root_dir, cubemap_file.replace('.props.txt', '.tga'))
                # BLENDER PATH GO
                args = [os.environ['BLENDER_PATH'], './blender/cube2sphere.blend', '--background', '--python', './blender/cube2sphere.py', '--']
                args.extend(faces)
                args.extend(['--output', output_path])
                subprocess.run(args, stdout=open(os.devnull, 'wb'))
            pbar.update(1)


def init(args: argparse.Namespace):
    pass


def add_common_arguments(parser: ArgumentParser):
    parser.add_argument('--dry', required=False, action='store_true', default=False)
    parser.add_argument('--clean', required=False, action='store_true', default=False)


if __name__ == '__main__':
    parser = ArgumentParser(prog='bdk')
    parser.add_argument('--mod', required=False, help='mod name (e.g., DarkestHourDev)')
    parser.add_argument('--verbose', required=False, action='store_true', default=False)

    subparsers = parser.add_subparsers(required=True, dest='command', title='command')

    dirty_parser = subparsers.add_parser('dirty')
    dirty_parser.add_argument('package')
    dirty_parser.set_defaults(func=dirty)

    export_parser = subparsers.add_parser('export')
    add_common_arguments(export_parser)
    export_parser.set_defaults(func=export)

    build_cubemaps_parser = subparsers.add_parser('build-cubemaps')
    build_cubemaps_parser.set_defaults(func=build_cubemaps)

    build_parser = subparsers.add_parser('build')
    add_common_arguments(build_parser)
    build_parser.set_defaults(func=build)

    env_parser = subparsers.add_parser('env')
    env_parser.set_defaults(func=env)

    init_parser = subparsers.add_parser('init')
    init_parser.set_defaults(func=init)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
    else:
        args.func(args)
