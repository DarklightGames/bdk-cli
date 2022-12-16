import os
import pickle
import subprocess
import sys
import time
import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Dict, List
from pathlib import Path


class BuildManifest:
    class Package:
        def __init__(self):
            self.last_modified_time = 0.0
            self.size = 0

    def __init__(self):
        self.packages: Dict[str, BuildManifest.Package] = {}


def load_manifest(build_directory: str) -> BuildManifest:
    manifest = BuildManifest()
    manifest_path = Path(os.path.join(build_directory, 'build.manifest')).resolve()
    print(manifest_path)
    if os.path.isfile(build_directory):
        with open(manifest_path, 'r') as file:
            try:
                manifest = pickle.load(file)
            except pickle.UnpicklingError as e:
                print(f'Failed to load build manifest: {e}', file=sys.stderr)
            print('Build manifest loaded')
    return manifest


def save_manifest(manifest: BuildManifest, build_directory: str):
    manifest_path = Path(os.path.join(build_directory, 'build.manifest')).resolve()
    with open(manifest_path, 'wb') as file:
        pickle.dump(manifest, file)


def export_package(output_path: str, package_path: str):
    root_dir = os.environ['ROOT_DIR']
    args = [os.environ['UMODEL_PATH'], '-export', f'-out="{output_path}"', f'-path={root_dir}', package_path]
    return subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def export_assets(mod: Optional[str] = None, dry: bool = False, clean: bool = False) -> List[Path]:
    root_directory = os.environ['ROOT_DIR']
    build_directory = os.environ['BUILD_DIR']

    if clean:
        manifest = BuildManifest()
    else:
        manifest = load_manifest(build_directory)

    print(len(manifest.packages))

    suffixes = ['.usx', '.utx']
    package_paths = list(p.resolve() for p in Path(root_directory).glob("**/*") if p.suffix in suffixes)

    package_paths_to_build = []

    # Compile a list of packages that are out of date with the manifest.
    for package_path in package_paths:
        basename = os.path.basename(package_path)
        package = manifest.packages.get(basename, None)
        should_build_package = False
        if package:
            if os.path.getmtime(package_path) != package.last_modified_time or os.path.getsize(package_path) != package.size:
                should_build_package = True
        else:
            package = BuildManifest.Package()
            should_build_package = True

        if should_build_package:
            package_paths_to_build.append(package_path)

        # Update the package stats in the manifest.
        package.last_modified_time = os.path.getmtime(package_path)
        package.size = os.path.getsize(package_path)

        manifest.packages[basename] = package

    print(f'{len(package_paths)} package(s) | {len(package_paths_to_build)} package(s) out-of-date')

    time.sleep(0.1)

    with tqdm.tqdm(total=len(package_paths_to_build)) as pbar:
        with ThreadPoolExecutor(max_workers=8) as executor:
            jobs = {executor.submit(export_package, build_directory, str(package_path)): package_path for package_path in package_paths_to_build}
            for _ in as_completed(jobs):
                pbar.update(1)

    save_manifest(manifest, build_directory)

    return package_paths_to_build


def build_assets(mod: Optional[str] = None, dry: bool = False, clean: bool = False):
    package_paths_to_build = export_assets(mod, dry, clean)
    # Now blend the assets.
    for package_path in package_paths_to_build:

        package_name = os.path.splitext(os.path.basename(package_path))[0]
        package_build_path = os.path.join(os.environ['BUILD_DIR'], package_name)

        if not package_name.endswith('_stc'):
            continue

        blender_path = os.environ['BLENDER_PATH']
        script_path = './blender/blend.py'
        input_directory = package_build_path
        library_directory = os.environ['LIBRARY_DIR']
        package_type = 'StaticMesh'  # TODO: get this from somewhere real
        output_path = os.path.join(library_directory, package_type, f'{package_name}.blend')

        script_args = ['build', input_directory, '--output_path', output_path]
        args = [blender_path, '--background', '--python', script_path, '--'] + script_args
        subprocess.Popen(args).communicate()
