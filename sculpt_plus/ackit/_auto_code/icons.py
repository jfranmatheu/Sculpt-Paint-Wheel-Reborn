''' Previews Manager. '''
from pathlib import Path
import os
import platform
import shelve
from string import Template
from enum import Enum
import numpy as np
import inspect

import bpy
from bpy.types import Image as BlImage, UILayout
from gpu.types import GPUTexture, Buffer as GPUBuffer
from bpy.utils import previews

from .._globals import GLOBALS
from ..debug import print_debug


# ----------------------------------------------------------------
# IMPORT CODE.

''' Previews Manager. '''

icon_previews = {}
icon_gputex = {}
icon_sizes = {}

GPUTEX_ICON_SIZE = 100, 100


class IconsViewer:
    @classmethod
    def draw_icons_in_layout(cls, layout: UILayout):
        box = layout.box()
        box.label(text="I c o n s   P r e v i e w s :")
        for icons_enum in cls.__dict__.values():
            if inspect.isclass(icons_enum):
                collection = box.column(align=True)
                collection.box().row(align=True).label(text="Collection '%s'" % icons_enum.__name__)
                grid_layout = collection.box().column(align=True).grid_flow(columns=0)
                for icon in icons_enum:
                    icon.draw_in_layout(grid_layout)


class IconsEnum(Enum):
    @property
    def collection(self) -> str:
        return self.__class__.__name__

    def __call__(self) -> tuple[str, str]:
        return self.identifier, self.filename

    @property
    def filepath(self) -> str | None:
        path: Path = GLOBALS.ADDON_SOURCE_PATH / self.value
        if path.exists() and path.is_file():
            return str(path)
        return None

    @property
    def identifier(self) -> str:
        return self.name

    @property
    def filename(self) -> str:
        return os.path.basename(self.filepath)

    @property
    def icon_id(self) -> int:
        collection: previews.ImagePreviewCollection = icon_previews.get(self.collection, None)
        if collection is None:
            collection: previews.ImagePreviewCollection = previews.new()
            icon_previews[self.collection] = collection
        elif preview := collection.get(self.identifier, None):
            return preview.icon_id
        filepath = self.filepath
        if filepath is None:
            return 0
        return collection.load(self.identifier, filepath, 'IMAGE', force_reload=True).icon_id

    @property
    def gputex(self) -> GPUTexture:
        collection: dict = icon_gputex.get(self.collection, None)
        if collection is None:
            icon_gputex[self.collection] = {}
        elif gputex := collection.get(self.identifier, None):
            return gputex

        # Load GPUTexture.
        filepath = self.filepath
        if filepath is None:
            print("Invalid file path... bad gputex")
            return None

        image: BlImage = bpy.data.images.load(filepath)
        image.scale(*GPUTEX_ICON_SIZE)
        px_count: int = len(image.pixels)
        pixels = np.empty(shape=px_count, dtype=np.float32)
        image.pixels.foreach_get(pixels)

        buff: GPUBuffer = GPUBuffer(
            'FLOAT',
            px_count,
            pixels
        )

        gputex: GPUTexture = GPUTexture(
            GPUTEX_ICON_SIZE,
            layers=0,
            is_cubemap=False,
            format='RGBA16F',
            data=buff
        )

        bpy.data.images.remove(image)
        del image

        # Cache GPUTexture.
        icon_gputex[self.collection][self.identifier] = gputex
        return gputex

    def draw_in_layout(self, layout: UILayout, scale: float = 2.0):
        if icon_id := self.icon_id:
            layout.template_icon(icon_id, scale=scale)


def unregister():
    for collection in icon_previews.values():
        previews.remove(collection)
    icon_previews.clear()
    icon_gputex.clear()



# ----------------------------------------------------------------

template_icons_py = Template("""# /icons.py
# Code automatically generated!
from pathlib import Path
from ${package}.icons import IconsEnum, IconsViewer

icons_dirpath = Path("${icons_dirpath}")


class Icons(IconsViewer):
${icon_enums}
""")

template_icons_enum = Template("""
\tclass ${cat_name}(IconsEnum):
${icons}
""")


class IconData:
    def __init__(self, icon_path: Path):
        idname = icon_path.stem
        if idname.startswith('[') and ']' in idname:
            idname = idname[idname.index(']')+1:]
        elif idname.startswith('(') and ')' in idname:
            idname = idname[idname.index(')')+1:]
        if ' ' in idname:
            idname = idname.replace(' ', '_')
        if '-' in idname:
            idname = idname.replace('-', '_')
        if '.' in idname:
            idname = idname.replace('.', '_')
        self.path = icon_path
        self.idname = idname.upper()
        self.name = icon_path.name
        self.ext = icon_path.suffix
        self.date = creation_date(str(icon_path))

    @property
    def filepath(self) -> str:
        return GLOBALS.ICONS_PATH.joinpath(self.name)


def creation_date(path_to_file):
    """
    Try to get the date that a file was created, falling back to when it was
    last modified if that isn't possible.
    """
    if platform.system() == 'Windows':
        return os.path.getctime(path_to_file)
    else:
        stat = os.stat(path_to_file)
        try:
            return stat.st_birthtime
        except AttributeError:
            # We're probably on Linux. No easy way to get creation dates here,
            # so we'll settle for when its content was last modified.
            return stat.st_mtime



def generate_icons_py(filename: str = 'icons.py'):
    ''' Generates the icons.py file in the root directory of your addon,
        also an Icon class inside from where you can get icons to draw in Blender interface
        as well as custom interfaces.

        Arguments:
        - 'relative_path': relative path to the icons folder, split folder by folder:
            example: init_icons('lib', 'icons').
    '''
    icons_path: Path = GLOBALS.ICONS_PATH
    icons_output_py: Path = GLOBALS.ADDON_SOURCE_PATH / f'{filename}.py'

    # Suppose addon_utils is a direct submodule of the addon module.
    icons: list[IconData] = []
    icons_per_category: dict[str, list[IconData]] = {} # defaultdict(list)

    print_debug("Searching icons from...", str(icons_path))
    if not os.path.exists(icons_path):
        print_debug("No icons found at path '%s'" % icons_path)
        return

    def _add_icons_from_directory(dirpath: Path, category_name: str = 'MAIN', is_subdir: bool = False):
        _icons = []
        for icon_path in dirpath.iterdir():
            if icon_path.is_file():
                if icon_path.suffix in {'.png', '.jpg', '.jpeg'}:
                    icon = IconData(icon_path)
                    if is_subdir:
                        icon.name = icon_path.parent.name + '/' + icon.name
                    _icons.append(icon)
            elif icon_path.is_dir():
                new_cat_name: str = icon_path.stem.upper().replace(' ', '_')
                _add_icons_from_directory(icon_path, category_name=new_cat_name, is_subdir=True)
        if _icons != []:
            icons.extend(_icons)
            icons_per_category[category_name] = _icons

    _add_icons_from_directory(icons_path, category_name='MAIN')

    if not icons:
        print_debug("No icons found!")
        return

    icons_data_file = icons_path / 'icons_data'
    modified_icons: list[IconData] = []

    with shelve.open(str(icons_data_file)) as icons_db:
        # Check icons that changed since last generation.
        for icon in icons:
            if saved_icon := icons_db.get(icon.idname, None):
                if icon.date != saved_icon.date:
                    # Modified icon.
                    icons_db[icon.idname] = icon
                    modified_icons.append(icon)
            else:
                # New Icon.
                icons_db[icon.idname] = icon
                modified_icons.append(icon)

    if not modified_icons:
        print_debug("No modified icons found!")
        return

    # Generate icons.py file.
    icons_py_code = template_icons_py.substitute(
        # get relative package path to ackit module.
        package=__package__[__package__.index('.ackit.'):], # __package__ : for absolute package path.
        icons_dirpath=icons_path.relative_to(GLOBALS.ADDON_SOURCE_PATH).as_posix(),
        icon_enums=''.join(
            [
                template_icons_enum.substitute(
                    cat_name=cat_name,
                    icons='\n'.join([f'\t\t{icon.idname} = icons_dirpath / "{icon.name}"' for icon in cat_icons])
                )
                for cat_name, cat_icons in icons_per_category.items()
            ]
        )
    )
    with icons_output_py.open('w') as f:
        f.write(icons_py_code)
