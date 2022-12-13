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
    root_directory = os.environ['ROOT_DIR']
    build_directory = os.environ['BUILD_DIR']
    from build import build_assets
    build_assets(path=root_directory, build_directory=build_directory, dry=args.dry, mod=args.mod)


def init(args: argparse.Namespace):
    pass


if __name__ == '__main__':
    parser = ArgumentParser(prog='bdk')
    parser.add_argument('--mod', required=False, help='mod name (e.g., DarkestHourDev)')
    parser.add_argument('--verbose', required=False, action='store_true', default=False)
    subparsers = parser.add_subparsers(required=True, dest='command', title='command')
    build_parser = subparsers.add_parser('build')
    build_parser.add_argument('--dry', required=False, action='store_true', default=False)
    build_parser.add_argument('--clean', required=False, action='store_true', default=False)
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