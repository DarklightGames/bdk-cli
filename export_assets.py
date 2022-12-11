import os

import tqdm
import concurrent.futures
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor


def export_assets(path: str, output_path: str, dry: bool, verbose: bool = False):
    suffixes = ['.usx', '.utx', '.ukx']
    files = list(p.resolve() for p in Path(path).glob("**/*") if p.suffix in suffixes)

    def export_package(output_path: str, package_path: str):
        args = [os.environ['UMODEL_PATH'], '-export', f'-out="{output_path}"', package_path]
        return subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    with tqdm.tqdm(total=len(files)) as pbar:
        with ThreadPoolExecutor(max_workers=8) as executor:
            jobs = {executor.submit(export_package, output_path, str(file)): file for file in files}
            for future in concurrent.futures.as_completed(jobs):
                pbar.update(1)
