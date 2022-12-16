import enum
import glob
import os
import typing
from pathlib import Path
from typing import get_type_hints, Any

from data import UTexture, UMaterial, UCombiner, UFinalBlend, UShader, UTexOscillator, UTexPanner, UTexScaler, \
    UConstantColor, URotator


def transform_value(property_type: type, value: Any):
    if property_type == int:
        return int(value)
    elif property_type == bool:
        return bool(value)
    elif property_type == float:
        return float(value)
    elif property_type == str:
        return value
    elif property_type.__class__ == enum.EnumMeta:
        return property_type[str(value).split(' ')[0]]
    elif property_type.__class__ == typing._UnionGenericAlias and len(property_type.__args__) == 2 and \
            property_type.__args__[1] == type(None):
        if value is None:
            return None
        return transform_value(property_type.__args__[0], value)
    elif property_type == URotator:
        return URotator.from_string(value)
    else:
        raise RuntimeError(f'Unhandled type: {property_type}')


class MaterialReader:
    def __init__(self):
        pass

    def read(self, material_type: type, path: str):
        if not issubclass(material_type, UMaterial):
            raise TypeError(f'{material_type} is not a material type')
        lines = Path(path).read_text().splitlines()
        props = {}
        for line in lines:
            key, value = line.split(' = ', maxsplit=1)
            props[key] = value
        material = material_type()
        material_type_hints = get_type_hints(type(material))
        for name, value in props.items():
            try:
                property_type = material_type_hints[name]
                value = transform_value(property_type, value)
                setattr(material, name, value)
            except KeyError:
                continue
        return material


if __name__ == '__main__':
    root_path = r'C:\dev\bdk-git\bdk-build\DH_Landscape_tex'
    materials = []

    reader = MaterialReader()

    __material_type_map__: typing.Dict[str, type] = {
        'Combiner': UCombiner,
        'FinalBlend': UFinalBlend,
        'Shader': UShader,
        'TexOscillator': UTexOscillator,
        'TexPanner': UTexPanner,
        'TexScaler': UTexScaler,
        'Texture': UTexture,
        'ConstantColor': UConstantColor
    }

    for file in glob.glob(os.path.join(root_path, '**/*.props.txt')):
        material_type = __material_type_map__[Path(file).parts[-2]]
        material = reader.read(material_type, file)
        print('=' * 8)
        print(file)
        print(material)
