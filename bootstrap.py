import shutil
import tempfile

import requests
from pathlib import Path

from tqdm import tqdm

umodel_url = 'https://seafile.darklightgames.com/d/69b3b60f652b4cef8b4c/files/?p=%2Fumodel_64.exe&dl=1'
blender_url =  'https://seafile.darklightgames.com/d/69b3b60f652b4cef8b4c/files/?p=%2Fblender-3.6-bdk.zip&dl=1'
bdk_addon_url = 'https://seafile.darklightgames.com/d/69b3b60f652b4cef8b4c/files/?p=%2Fbdk.zip&dl=1'

def download(url, filename, desc=None):
    response = requests.get(url, stream=True)
    chunk_size = 1024

    if response.status_code != 200:
        response.raise_for_status()
        raise RuntimeError('Bad response from server')

    file_size = int(response.headers.get('content-length', 0))

    path = Path(filename).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(filename, 'wb') as file, tqdm(
        desc=desc,
        total=file_size,
        unit='iB',
        unit_scale=True,
        unit_divisor=1024,
    ) as bar:
        for data in response.iter_content(chunk_size):
            size = file.write(data)
            bar.update(size)


def install_umodel():
    umodel_filename = './bin/umodel.exe'
    download(umodel_url, umodel_filename, 'umodel')

def install_blender():
    blender_filename = tempfile.mktemp(suffix='.zip')
    download(blender_url, blender_filename, 'blender')
    shutil.unpack_archive(blender_filename, './bin/blender')
    Path(blender_filename).unlink()

def install_bdk_cli():
    pass

if __name__ == '__main__':
    install_umodel()
    install_blender()
