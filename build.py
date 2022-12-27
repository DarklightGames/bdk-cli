import fnmatch
import json
import os
import subprocess
import time
import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Dict, List
from pathlib import Path


MANIFEST_FILENAME = '.bdkmanifest'


class BuildManifest(dict):

    class Package(dict):
        def __init__(self):
            dict.__init__(self, last_modified_time=0.0, size=0, is_built=False)

        @property
        def last_modified_time(self) -> float:
            return self['last_modified_time']

        @property
        def size(self) -> int:
            return self['size']

        @property
        def is_built(self) -> bool:
            return self['is_built']

        @is_built.setter
        def is_built(self, value: bool):
            self['is_built'] = value

        @last_modified_time.setter
        def last_modified_time(self, value: float):
            self['last_modified_time'] = value

        @size.setter
        def size(self, value: int):
            self['size'] = value

    def __init__(self, packages):
        dict.__init__(self, packages=packages)

    @property
    def packages(self) -> Dict[str, Package]:
        return self['packages']

    def mark_package_as_built(self, package_relative_directory: str):
        if package_relative_directory in self.packages:
            self.packages[package_relative_directory]['is_built'] = True

    @staticmethod
    def load_from_directory(build_directory: str) -> 'BuildManifest':
        packages = {}
        manifest_path = Path(os.path.join(build_directory, MANIFEST_FILENAME)).resolve()
        if os.path.isfile(manifest_path):
            with open(manifest_path, 'r') as file:
                try:
                    data = json.load(file)
                    packages = data['packages']
                except UnicodeDecodeError as e:
                    print(e)
                print('Build manifest loaded')
        else:
            print('Build manifest file not found')
        return BuildManifest(packages)

    def save_to_directory(self, build_directory: str):
        manifest_path = Path(os.path.join(build_directory, MANIFEST_FILENAME)).resolve()
        with open(manifest_path, 'w') as file:
            json.dump(self, file, indent=2)


# Dirties a single package so that it is marked for re-export.
def dirty_package(package_name_search: str):
    build_directory = str(Path(os.environ['BUILD_DIR']).resolve())
    manifest = BuildManifest.load_from_directory(build_directory)
    for package_path, _ in manifest.packages.items():
        package_name = os.path.splitext(os.path.basename(package_path))[0]
        if package_name == package_name_search:
            print(f'Dirtied {package_path}')
            manifest.packages.pop(package_path)
            break
    manifest.save_to_directory(build_directory)


def export_package(output_path: str, package_path: str):
    root_dir = str(Path(os.environ['ROOT_DIR']).resolve())
    args = [os.environ['UMODEL_PATH'], '-export', '-nolinked', f'-out="{output_path}"', f'-path={root_dir}', package_path]
    return subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def export_assets(mod: Optional[str] = None, dry: bool = False, clean: bool = False) -> List[str]:
    root_directory = str(Path(os.environ['ROOT_DIR']).resolve())
    build_directory = str(Path(os.environ['BUILD_DIR']).resolve())

    if clean:
        manifest = BuildManifest(packages={})
    else:
        manifest = BuildManifest.load_from_directory(build_directory)

    suffixes = ['.usx', '.utx', '.rom']
    # suffixes = ['.rom']
    package_paths = set(str(p.resolve()) for p in Path(root_directory).glob("**/*") if p.suffix in suffixes)
    package_paths_to_build = []

    ignore_patterns = set()
    bdkignore_path = os.path.join(root_directory, '.bdkignore')
    if os.path.isfile(bdkignore_path):
        with open(bdkignore_path, 'r') as f:
            ignore_patterns = map(lambda x: x.strip(), f.readlines())

    # Filter out packages based on patterns in the .bdkignore file in the root directory.
    for ignore_pattern in ignore_patterns:
        package_paths = package_paths.difference(fnmatch.filter(package_paths, ignore_pattern))

    # Compile a list of packages that are out of date with the manifest.
    for package_path in package_paths:
        package_path_relative = os.path.relpath(package_path, root_directory)
        package = manifest.packages.get(package_path_relative, None)
        should_build_package = False
        if package:
            if os.path.getmtime(package_path) != package['last_modified_time'] or \
                    os.path.getsize(package_path) != package['size']:
                should_build_package = True
        else:
            package = BuildManifest.Package()
            should_build_package = True

        if should_build_package:
            package_paths_to_build.append(package_path)

        # Update the package stats in the manifest.
        package['last_modified_time'] = os.path.getmtime(package_path)
        package['size'] = os.path.getsize(package_path)

        manifest.packages[package_path_relative] = package

    print(f'{len(package_paths)} package(s) | {len(package_paths_to_build)} package(s) out-of-date')

    time.sleep(0.1)

    if not dry and len(package_paths_to_build) > 0:
        with tqdm.tqdm(total=len(package_paths_to_build)) as pbar:
            with ThreadPoolExecutor(max_workers=8) as executor:
                jobs = []
                for package_path in package_paths_to_build:
                    package_build_directory = os.path.dirname(os.path.relpath(package_path, root_directory))
                    os.makedirs(package_build_directory, exist_ok=True)
                    jobs.append(executor.submit(export_package, os.path.join(build_directory, package_build_directory), str(package_path)))
                for _ in as_completed(jobs):
                    pbar.update(1)

        manifest.save_to_directory(build_directory)

    return package_paths_to_build


def build_assets(mod: Optional[str] = None, dry: bool = False, clean: bool = False):

    # First export the assets.
    export_assets(mod, dry, clean)

    build_directory = str(Path(os.environ['BUILD_DIR']).resolve())

    manifest = BuildManifest.load_from_directory(build_directory)

    # TQDM this once we sort all the errors
    # Build a list of packages that have been exported but haven't been built yet.
    package_paths_to_build = []
    for package_path, package in manifest.packages.items():
        if not package['is_built']:
            package_paths_to_build.append(package_path)

    # Now blend the assets.
    for package_path in package_paths_to_build:
        package_name = os.path.basename(package_path)
        package_build_path = str(Path(os.path.join(os.environ['BUILD_DIR'], package_path)).resolve())

        script_path = './blender/blend.py'

        input_directory = os.path.splitext(package_build_path)[0]
        output_path = os.path.join(os.environ['LIBRARY_DIR'], Path(package_path).with_suffix('.blend'))
        output_path = str(Path(output_path).resolve())

        script_args = ['build', input_directory, '--output_path', output_path]

        args = [os.environ['BLENDER_PATH'], '--background', './blender/build_template.blend', '--python', script_path, '--'] + script_args
        if subprocess.call(args) == 0:
            manifest.mark_package_as_built(package_path)
        else:
            print('BUILD FAILED FOR ' + package_name)
            pass

    manifest.save_to_directory(build_directory)
