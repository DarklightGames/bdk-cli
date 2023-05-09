import fnmatch
import json
import os
import re
import shutil
import subprocess
import time
from glob import glob

import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Dict, List
from pathlib import Path

from bdk import UReference

MANIFEST_FILENAME = '.bdkmanifest'


class BuildManifest(dict):

    class File(dict):
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

    def __init__(self, files):
        dict.__init__(self, files=files)

    @property
    def files(self) -> Dict[str, File]:
        return self['files']

    def mark_file_as_built(self, file: str):
        if file in self.files:
            self.files[file]['is_built'] = True

    @staticmethod
    def load() -> 'BuildManifest':
        build_directory = str(Path(os.environ['BUILD_DIRECTORY']).resolve())
        packages = {}
        manifest_path = Path(os.path.join(build_directory, MANIFEST_FILENAME)).resolve()

        if os.path.isfile(manifest_path):
            with open(manifest_path, 'r') as file:
                try:
                    data = json.load(file)
                    packages = data['files']
                except UnicodeDecodeError as e:
                    print(e)
                print('Build manifest loaded')
        else:
            print('Build manifest file not found')

        return BuildManifest(packages)

    def save(self):
        build_directory = str(Path(os.environ['BUILD_DIRECTORY']).resolve())
        manifest_path = Path(os.path.join(build_directory, MANIFEST_FILENAME)).resolve()
        with open(manifest_path, 'w') as file:
            json.dump(self, file, indent=2)


def rebuild_assets(mod, dry, clean):
    manifest = BuildManifest.load()
    for package_path, package in manifest['files'].items():
        package['is_built'] = False
    build_assets(mod, dry, clean)


def export_package(output_path: str, package_path: str):
    root_dir = str(Path(os.environ['ROOT_DIRECTORY']).resolve())
    umodel_path = Path(os.environ['UMODEL_PATH']).resolve()
    args = [str(umodel_path), '-export', '-nolinked', f'-out="{output_path}"', f'-path="{root_dir}"', package_path]
    return subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def export_assets(mod: Optional[str] = None, dry: bool = False, clean: bool = False, name_filter: Optional[str] = None) -> List[str]:
    root_directory = str(Path(os.environ['ROOT_DIRECTORY']).resolve())
    build_directory = str(Path(os.environ['BUILD_DIRECTORY']).resolve())

    # TODO: only clean the packages that we want to build (e.g. name_filter)
    if clean:
        manifest = BuildManifest(files={})
    else:
        manifest = BuildManifest.load()

    # TODO: remove package references that no longer exist, and delete their associated bdk-build data.
    manifest_files = [x for x in manifest.files]
    for file in manifest_files:
        path = Path(root_directory, file)
        if not path.is_file():
            print(f"{path} no longer exists!")
            package_build_directory = Path(build_directory, file).with_suffix('')
            if package_build_directory.is_dir():
                shutil.rmtree(package_build_directory)
            manifest.files.pop(file)

    # Read ignore patterns from the .bdkignore file.
    bdkignore_filename = '.bdkignore'
    ignore_patterns = set()
    bdkignore_path = os.path.join(root_directory, bdkignore_filename)
    if os.path.isfile(bdkignore_path):
        with open(bdkignore_path, 'r') as f:
            ignore_patterns = map(lambda x: x.strip(), f.readlines())

    asset_paths = [
        "Animations",
        "StaticMeshes",
        "Textures",
        "Sounds"
    ]

    if mod is not None:
        asset_paths += [mod]

    # Get a list of packages with matching suffixes in the root directory.
    package_suffixes = ['.usx', '.utx', '.rom']
    package_paths = set()

    for asset_path in asset_paths:
        package_paths = package_paths.union(set(str(p.resolve()) for p in Path(root_directory, asset_path).glob("**/*") if p.suffix in package_suffixes))

    # Filter out packages based on patterns in the .bdkignore file in the root directory.
    for ignore_pattern in ignore_patterns:
        package_paths = package_paths.difference(fnmatch.filter(package_paths, ignore_pattern))

    # Compile a list of packages that are out of date with the manifest.
    packages_to_build = []
    for package_path in package_paths:
        if name_filter is not None and not fnmatch.fnmatch(os.path.basename(package_path), name_filter):
            continue
        package_path_relative = os.path.relpath(package_path, root_directory)
        file = manifest.files.get(package_path_relative, None)
        should_build_file = False

        if file:
            if os.path.getmtime(package_path) != file['last_modified_time'] or \
                    os.path.getsize(package_path) != file['size']:
                should_build_file = True
        else:
            file = BuildManifest.File()
            should_build_file = True

        if clean:
            should_build_file = True

        if should_build_file:
            packages_to_build.append(package_path)

        # Update the file stats in the manifest.
        file['last_modified_time'] = os.path.getmtime(package_path)
        file['size'] = os.path.getsize(package_path)

        manifest.files[package_path_relative] = file

    print(f'{len(package_paths)} file(s) | {len(packages_to_build)} file(s) out-of-date')

    # This is here so tqdm displays correctly inside PyCharm terminals,
    # otherwise it gets all messed up.
    time.sleep(0.1)

    if not dry and len(packages_to_build) > 0:
        with tqdm.tqdm(total=len(packages_to_build)) as pbar:
            with ThreadPoolExecutor(max_workers=8) as executor:
                jobs = []
                for package_path in packages_to_build:
                    package_build_directory = os.path.join(
                        build_directory,
                        os.path.dirname(os.path.relpath(package_path, root_directory))
                    )
                    os.makedirs(package_build_directory, exist_ok=True)
                    jobs.append(executor.submit(export_package, package_build_directory, str(package_path)))
                for _ in as_completed(jobs):
                    pbar.update(1)

    if not dry:
        manifest.save()

    return packages_to_build


def build_cube_maps(clean: bool = False):
    manifest = BuildManifest.load()

    pattern = '**/Cubemap/*.props.txt'
    build_directory = Path(os.environ['BUILD_DIRECTORY']).resolve()
    cubemap_file_paths = []
    for cubemap_file_path in glob(pattern, root_dir=build_directory, recursive=True):
        cubemap_file_paths.append(cubemap_file_path)

    print(f'Found {len(cubemap_file_paths)} cubemap(s)')

    # Filter out cube maps that have already been built
    cubemap_file_paths_to_build = []
    for cubemap_file_path in cubemap_file_paths:
        file_path = os.path.join(build_directory, cubemap_file_path)
        mtime = os.path.getmtime(file_path)
        size = os.path.getsize(file_path)
        if cubemap_file_path in manifest.files:
            file = manifest.files[cubemap_file_path]
            if clean or mtime != file['last_modified_time'] or size != file['size'] or not file['is_built']:
                # Update the file stats in the manifest.
                file['last_modified_time'] = mtime
                file['size'] = size
                cubemap_file_paths_to_build.append(cubemap_file_path)
        else:
            # New file, load it into the manifest.
            file = BuildManifest.File()
            file.last_modified_time = mtime
            file.size = size
            file.is_built = False
            manifest.files[cubemap_file_path] = file

            cubemap_file_paths_to_build.append(cubemap_file_path)

    print(f'{len(cubemap_file_paths_to_build)} cubemap(s) marked for rebuilding')

    with tqdm.tqdm(total=len(cubemap_file_paths_to_build)) as pbar:
        for cubemap_file in cubemap_file_paths_to_build:
            relative_package_directory = Path(cubemap_file).parent.parent
            with open(os.path.join(os.environ['BUILD_DIRECTORY'], cubemap_file), 'r') as f:
                contents = f.read()
                textures = re.findall(r'Faces\[\d] = ([\w\d]+\'[\w\d_\-.]+\')', contents)
                faces = []
                for texture in textures:
                    face_reference = UReference.from_string(texture)
                    image_path = os.path.join(
                        build_directory,
                        relative_package_directory,
                        face_reference.type_name,
                        f'{face_reference.object_name}.tga'
                    )
                    faces.append(image_path)
                output_path = os.path.join(build_directory, cubemap_file.replace('.props.txt', '.tga'))
                args = [
                    os.environ['BLENDER_PATH'],
                    './blender/cube2sphere.blend',
                    '--background',
                    '--python',
                    './blender/cube2sphere.py',
                    '--']

                args.extend(faces)
                args.extend(['--output', output_path])
                completed_process = subprocess.run(args, stdout=open(os.devnull, 'wb'))
                if completed_process.returncode == 0:
                    manifest.mark_file_as_built(cubemap_file)
            pbar.update(1)

    manifest.save()


def build_assets(
        mod: Optional[str] = None,
        dry: bool = False,
        clean: bool = False,
        no_export: bool = False,
        no_cubemaps: bool = False,
        name_filter: Optional[str] = None):

    # First export the assets.
    if not no_export:
        export_assets(mod, dry, clean)

    # Build the cube maps.
    if not no_cubemaps:
        build_cube_maps(clean)

    manifest = BuildManifest.load()

    # TODO: TQDM this once we sort all the errors
    # TODO: we need to exclude cubemaps from this!
    # Build a list of packages that have been exported but haven't been built yet.
    package_paths_to_build = []
    for file_path, file in manifest.files.items():
        if not file['is_built'] or clean:
            package_paths_to_build.append(file_path)

    if name_filter is not None:
        package_paths_to_build = fnmatch.filter(package_paths_to_build, name_filter)

    if len(package_paths_to_build) == 0:
        print('No packages marked to be built')

    # Order the packages so that texture packages are built first.
    # NOTE: It's possible for non-UTX packages to have textures in them.
    ext_order = ['.usx', '.utx', '.rom']
    package_paths_to_build = list(filter(lambda x: os.path.splitext(x)[1] in ext_order, package_paths_to_build))

    def package_extension_sort_key_cb(path: str):
        try:
            return ext_order.index(os.path.splitext(path)[1])
        except ValueError as e:
            return -1

    package_paths_to_build.sort(key=package_extension_sort_key_cb, reverse=True)

    success_count = 0
    failure_count = 0

    # Now blend the assets.
    for package_path in package_paths_to_build:
        package_name = os.path.basename(package_path)
        package_build_path = str(Path(os.path.join(os.environ['BUILD_DIRECTORY'], package_path)).resolve())

        script_path = './blender/blend.py'

        input_directory = os.path.splitext(package_build_path)[0]

        if os.path.splitext(package_path)[1] == '.rom':
            root_directory = os.environ['MAPS_DIRECTORY']
        else:
            root_directory = os.environ['LIBRARY_DIRECTORY']

        output_path = os.path.join(root_directory, Path(package_path).with_suffix('.blend'))
        output_path = str(Path(output_path).resolve())

        script_args = ['build', input_directory, '--output_path', output_path]

        args = [
                   os.environ['BLENDER_PATH'],
                   '--background',
                   './blender/build_template.blend',
                   '--python',
                   script_path,
                   '--'
               ] + script_args

        if subprocess.call(args) == 0:
            manifest.mark_file_as_built(package_path)
            success_count += 1
        else:
            print('BUILD FAILED FOR ' + package_name)
            failure_count += 1

    manifest.save()

    print(f'{success_count} Succeeded | {failure_count} Failed')
