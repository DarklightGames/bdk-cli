import argparse
import os

from dotenv import load_dotenv
from argparse import ArgumentParser

BLENDER_VERSION_MIN = '3.4.0'
UMODEL_VERSION_MIN = 1590
IO_SCENE_PSK_PSA_VERSION_MIN = '4.2.0'

load_dotenv()


def env(args: argparse.Namespace):
    # test that config is legit
    from env import test_environment
    print('Checking Environment')
    test_environment(verbose=args.verbose)


def build(args: argparse.Namespace):
    root_dir = os.environ['ROOT_DIR']
    build_dir = os.environ['BUILD_DIR']
    from export_assets import export_assets
    export_assets(path=root_dir, output_path=build_dir, dry=args.dry)


if __name__ == '__main__':
    parser = ArgumentParser(prog='bdk')
    parser.add_argument('--mod', required=False)
    parser.add_argument('--verbose', required=False, action='store_true', default=False)
    subparsers = parser.add_subparsers(required=True, dest='command')
    build_parser = subparsers.add_parser('build')
    build_parser.add_argument('--dry', required=False, action='store_true', default=False)
    build_parser.add_argument('--clean', required=False, action='store_true', default=False)
    build_parser.set_defaults(func=build)
    test_parser = subparsers.add_parser('env')
    test_parser.set_defaults(func=env)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
    else:
        args.func(args)
