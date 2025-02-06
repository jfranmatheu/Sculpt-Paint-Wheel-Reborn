from os.path import basename, exists, isfile

import bpy.utils.previews


previews = None


def get_preview_id_from_image_path(image_path: str) -> int:
    if not exists(image_path) or not isfile(image_path):
        return 0
    global previews
    idname: str = basename(image_path)
    if idname in previews:
        return previews[idname].icon_id
    return previews.load(idname, image_path, 'IMAGE').icon_id


def register():
    global previews
    previews = bpy.utils.previews.new()


def unregister():
    global previews
    if previews is not None:
        previews.close()
        previews = None
