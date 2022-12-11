import os
import subprocess
import sys
import pathlib
import semver
import re
from colorama import Fore, Style

import bdk


def get_blender_version(verbose=False) -> semver.VersionInfo:
    if 'BLENDER_PATH' not in os.environ:
        raise RuntimeError('BLENDER_PATH is not in environment')
    blender_path = pathlib.Path(os.environ['BLENDER_PATH']).resolve()
    if not blender_path.is_file():
        raise RuntimeError(f'BLENDER_PATH is not a file ({blender_path})')
    p = subprocess.run([blender_path, '--version'], capture_output=True)
    if p.returncode != 0:
        raise RuntimeError('Blender version could not be determined')
    m = re.match(r'Blender (\d.\d.\d)', p.stdout.decode())
    version = semver.VersionInfo.parse(m.group(1))
    version_minimum = semver.VersionInfo.parse(bdk.BLENDER_VERSION_MIN)
    if version < version_minimum:
        raise RuntimeError(f'Blender must be at least version {version_minimum}, found {version}')
    return version


def get_umodel_version(verbose=False) -> int:
    if 'UMODEL_PATH' not in os.environ:
        raise RuntimeError('UMODEL_PATH is not in environment')
    umodel_path = pathlib.Path(os.environ['UMODEL_PATH']).resolve()
    if not umodel_path.is_file():
        raise RuntimeError(f'UMODEL_PATH is not a file')
    p = subprocess.run([umodel_path, '-version'], capture_output=True)
    m = re.search(r'\(build (\d+)\)', p.stdout.decode())
    if not m:
        raise RuntimeError(f'Could not determine umodel version')
    version = int(m.group(1))
    version_minimum = bdk.UMODEL_VERSION_MIN
    if version < version_minimum:
        raise RuntimeError(f'umodel must be at least version {version_minimum}, found {version}')
    return version


def test_environment(verbose=False):
    try:
        version = get_blender_version(verbose=verbose)
        print(f'{Fore.GREEN}Blender ({version}){Style.RESET_ALL}')
    except RuntimeError as e:
        print(f'{Fore.RED}Blender: {e}', file=sys.stderr)

    try:
        version = get_umodel_version(verbose=verbose)
        print(f'{Fore.GREEN}umodel ({version}){Style.RESET_ALL}')
    except RuntimeError as e:
        print(f'{Fore.RED}umodel: {e}', file=sys.stderr)
