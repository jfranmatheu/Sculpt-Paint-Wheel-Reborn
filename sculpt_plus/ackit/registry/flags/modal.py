from enum import Enum, auto
from typing import Type

import bpy

from ...registry.reg_types.ops import T


__all__ = ['ModalFlagsDecorators']


class ModalFlags(Enum):
    DRAW_POST_PIXEL = auto()
    DRAW_POST_VIEW = auto()
    DRAW_PRE_VIEW = auto()
    DRAW_BACKDROP = auto()


class ModalFlagsDecorators:
    """
    Decorators for adding modal operator flags which enable custom modal operator functionalities.
    """

    @staticmethod
    def _decorator(flag: ModalFlags, **kwargs):
        """
        Base decorator to enable custom modal operator functionalities.
        
        Args:
            flag (ModalFlags): The specific modal function flag to add.
        
        Returns:
            Callable: A decorator function that modifies the modal operator class to include the specified flags to the modal operator.
        """
        def wrapper(cls: Type[T]) -> Type[T]:
            if not hasattr(cls, '_modal_flags') or cls._modal_flags is None:
                cls._modal_flags = set()
            cls._modal_flags.add(flag)
            for key, value in kwargs.items():
                setattr(cls, key, value)
            return cls
        return wrapper

    class DRAW_POST_PIXEL(Enum):
        """ Enables draw_2d() function in the modal for the selected space. """
        VIEW_3D = bpy.types.SpaceView3D
        IMAGE_EDITOR = bpy.types.SpaceImageEditor
        CLIP_EDITOR = bpy.types.SpaceClipEditor
        CONSOLE = bpy.types.SpaceConsole
        DOPE_SHEET_EDITOR = bpy.types.SpaceDopeSheetEditor
        FILE_BROWSER = bpy.types.SpaceFileBrowser
        GRAPH_EDITOR = bpy.types.SpaceGraphEditor
        INFO = bpy.types.SpaceInfo
        NLA_EDITOR = bpy.types.SpaceNLA
        NODE_EDITOR = bpy.types.SpaceNodeEditor
        NODE_EDITOR_PATH = bpy.types.SpaceNodeEditorPath
        NODE_OVERLAY = bpy.types.SpaceNodeOverlay
        OUTLINER = bpy.types.SpaceOutliner
        SEQUENCE_EDITOR = bpy.types.SequenceEditor
        SPREADSHEET = bpy.types.SpaceSpreadsheet
        TEXT_EDITOR = bpy.types.SpaceTextEditor
        UV_EDITOR = bpy.types.SpaceUVEditor
        
        def __call__(self, _deco_cls):
            return ModalFlagsDecorators._decorator(ModalFlags.DRAW_POST_PIXEL, _draw_postpixel_space=self.value)(_deco_cls)

    class DRAW_POST_VIEW(Enum):
        """ Enables draw_3d() function in the modal for the selected space. """
        VIEW_3D = bpy.types.SpaceView3D
        IMAGE_EDITOR = bpy.types.SpaceImageEditor
        CLIP_EDITOR = bpy.types.SpaceClipEditor
        CONSOLE = bpy.types.SpaceConsole
        DOPE_SHEET_EDITOR = bpy.types.SpaceDopeSheetEditor
        FILE_BROWSER = bpy.types.SpaceFileBrowser
        GRAPH_EDITOR = bpy.types.SpaceGraphEditor
        INFO = bpy.types.SpaceInfo
        NLA_EDITOR = bpy.types.SpaceNLA
        NODE_EDITOR = bpy.types.SpaceNodeEditor
        NODE_EDITOR_PATH = bpy.types.SpaceNodeEditorPath
        NODE_OVERLAY = bpy.types.SpaceNodeOverlay
        OUTLINER = bpy.types.SpaceOutliner
        SEQUENCE_EDITOR = bpy.types.SequenceEditor
        SPREADSHEET = bpy.types.SpaceSpreadsheet
        TEXT_EDITOR = bpy.types.SpaceTextEditor
        UV_EDITOR = bpy.types.SpaceUVEditor
        
        def __call__(self, _deco_cls):
            return ModalFlagsDecorators._decorator(ModalFlags.DRAW_POST_VIEW, _draw_postview_space=self.value)(_deco_cls)

    class DRAW_PRE_VIEW(Enum):
        """ Enables draw_3d() function in the modal for the selected space. """
        VIEW_3D = bpy.types.SpaceView3D
        IMAGE_EDITOR = bpy.types.SpaceImageEditor
        CLIP_EDITOR = bpy.types.SpaceClipEditor
        CONSOLE = bpy.types.SpaceConsole
        DOPE_SHEET_EDITOR = bpy.types.SpaceDopeSheetEditor
        FILE_BROWSER = bpy.types.SpaceFileBrowser
        GRAPH_EDITOR = bpy.types.SpaceGraphEditor
        INFO = bpy.types.SpaceInfo
        NLA_EDITOR = bpy.types.SpaceNLA
        NODE_EDITOR = bpy.types.SpaceNodeEditor
        NODE_EDITOR_PATH = bpy.types.SpaceNodeEditorPath
        NODE_OVERLAY = bpy.types.SpaceNodeOverlay
        OUTLINER = bpy.types.SpaceOutliner
        SEQUENCE_EDITOR = bpy.types.SequenceEditor
        SPREADSHEET = bpy.types.SpaceSpreadsheet
        TEXT_EDITOR = bpy.types.SpaceTextEditor
        UV_EDITOR = bpy.types.SpaceUVEditor

        def __call__(self, _deco_cls):
            return ModalFlagsDecorators._decorator(ModalFlags.DRAW_PRE_VIEW, _draw_preview_space=self.value)(_deco_cls)

    class DRAW_BACKDROP(Enum):
        """ Enables draw_backdrop() function in the modal for the selected node editor type. """
        SHADER_NODE_TREE = 'ShaderNodeTree'
        GEOMETRY_NODE_TREE = 'GeometryNodeTree'
        TEXTURE_NODE_TREE = 'TextureNodeTree'

        def __call__(self, _deco_cls):
            return ModalFlagsDecorators._decorator(ModalFlags.DRAW_BACKDROP, _draw_backdrop_treetype=self.value)(_deco_cls)
