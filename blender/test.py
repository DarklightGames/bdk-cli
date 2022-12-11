import addon_utils

try:
    addon = next(filter(lambda addon: addon.__name__ == 'io_scene_psk_psa', addon_utils.modules()))
except StopIteration:
    raise RuntimeError('Blender addon "io_scene_psk_psa" is not installed')
version = addon.bl_info.get('version', None)
print(version)
