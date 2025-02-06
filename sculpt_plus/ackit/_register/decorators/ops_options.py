from enum import Enum, auto
from typing import Type

from ..types.ops import T


__all__ = ['OperatorOptionsDecorators']


class OperatorTypeFlags(Enum):
    # Official Blender Operator Type Flags
    # https://docs.blender.org/api/current/bpy_types_enum_items/operator_type_flag_items.html#rna-enum-operator-type-flag-items
    REGISTER = auto()          # Display in info window and support redo toolbar panel
    UNDO = auto()              # Push an undo event when operator returns FINISHED
    UNDO_GROUPED = auto()      # Push a single undo event for repeated instances
    BLOCKING = auto()          # Block anything else from using the cursor
    MACRO = auto()             # Check if operator is a macro
    GRAB_CURSOR = auto()       # Grab mouse focus, enables wrapping for continuous grab
    GRAB_CURSOR_X = auto()     # Grab and warp only X axis
    GRAB_CURSOR_Y = auto()     # Grab and warp only Y axis
    DEPENDS_ON_CURSOR = auto() # Use initial cursor location, prompt for cursor placement
    PRESET = auto()            # Display a preset button with operator settings
    INTERNAL = auto()          # Remove operator from search results
    MODAL_PRIORITY = auto()    # Handle events before other modal operators


class OperatorOptionsDecorators:
    @staticmethod
    def _decorator(flag: OperatorTypeFlags, **kwargs):
        """
        Base decorator to add Blender operator type flags.
        
        Args:
            flag (OperatorTypeFlags): The specific operator flag to add.
        
        Returns:
            Callable: A decorator function that modifies the operator class to include the specified flags to the operator.
        """
        def wrapper(cls: Type[T]) -> Type[T]:
            if not hasattr(cls, 'bl_options'):
                cls.bl_options = set()
            cls.bl_options.add(flag.name)
            for key, value in kwargs.items():
                setattr(cls, key, value)
            return cls
        return wrapper

    @classmethod
    def REGISTER(cls, _deco_cls):
        """
        Integrates operator into Blender's UI.
        Enables display in info window and redo panel.
        Supports operator history tracking.
        """
        return cls._decorator(OperatorTypeFlags.REGISTER)(_deco_cls)

    @classmethod
    def UNDO(cls, _deco_cls):
        """
        Creates an undo event for data-modifying operators.
        Enables operator reversal through Blender's undo system.
        Crucial for operators that change scene state.
        """
        return cls._decorator(OperatorTypeFlags.UNDO)(_deco_cls)

    @classmethod
    def UNDO_GROUPED(cls, _deco_cls):
        """
        Consolidates multiple similar operator executions.
        Reduces undo stack complexity.
        Improves performance for repetitive operations.
        """
        return cls._decorator(OperatorTypeFlags.UNDO_GROUPED)(_deco_cls)

    @classmethod
    def BLOCKING(cls, _deco_cls):
        """
        Exclusively controls cursor during operator execution.
        Prevents conflicting interactions.
        Ensures focused, uninterrupted operation.
        """
        return cls._decorator(OperatorTypeFlags.BLOCKING)(_deco_cls)

    @classmethod
    def MACRO(cls, _deco_cls):
        """
        Marks operator as a composite of multiple sub-operations.
        Enables complex, multi-step transformations.
        Supports workflow automation.
        """
        return cls._decorator(OperatorTypeFlags.MACRO)(_deco_cls)

    @classmethod
    def GRAB_CURSOR(cls, _deco_cls):
        """
        Captures mouse focus for continuous interactions.
        Enables cursor wrapping and seamless manipulation.
        Supports precise input-driven transformations.
        """
        return cls._decorator(OperatorTypeFlags.GRAB_CURSOR)(_deco_cls)

    @classmethod
    def GRAB_CURSOR_X(cls, _deco_cls):
        """
        Constrains cursor movement to horizontal axis.
        Provides controlled X-axis interactions.
        Useful for precise horizontal adjustments.
        """
        return cls._decorator(OperatorTypeFlags.GRAB_CURSOR_X)(_deco_cls)

    @classmethod
    def GRAB_CURSOR_Y(cls, _deco_cls):
        """
        Constrains cursor movement to vertical axis.
        Provides controlled Y-axis interactions.
        Useful for precise vertical adjustments.
        """
        return cls._decorator(OperatorTypeFlags.GRAB_CURSOR_Y)(_deco_cls)

    @classmethod
    def PRESET(cls, _deco_cls):
        """
        Adds preset button to operator settings.
        Allows saving and quick reuse of configurations.
        Enhances workflow efficiency.
        """
        return cls._decorator(OperatorTypeFlags.PRESET)(_deco_cls)

    @classmethod
    def INTERNAL(cls, _deco_cls):
        """
        Removes operator from public search results.
        Hides utility operators from direct user access.
        Useful for background or helper tools.
        """
        return cls._decorator(OperatorTypeFlags.INTERNAL)(_deco_cls)

    @classmethod
    def MODAL_PRIORITY(cls, _deco_cls):
        """
        Gives operator higher event handling priority.
        Processes events before other modal operators.
        Use sparingly and with careful consideration.
        """
        return cls._decorator(OperatorTypeFlags.MODAL_PRIORITY)(_deco_cls)

    class DEPENDS_ON_CURSOR(Enum):
        """
        Requires specific initial cursor placement.
        Enables context-sensitive transformations.
        Provides interactive tool initialization.
        """
        DEFAULT = "Default"
        NONE = "None"
        WAIT = "Wait"
        CROSSHAIR = "Crosshair"
        MOVE_X = "Move-X"
        MOVE_Y = "Move-Y"
        KNIFE = "Knife"
        TEXT = "Text"
        PAINT_BRUSH = "Paint Brush"
        PAINT_CROSS = "Paint Cross"
        DOT = "Dot Cursor"
        ERASER = "Eraser"
        HAND = "Open Hand"
        HAND_POINT = "Pointing Hand"
        HAND_CLOSED = "Closed Hand"
        SCROLL_X = "Scroll-X"
        SCROLL_Y = "Scroll-Y"
        SCROLL_XY = "Scroll-XY"
        EYEDROPPER = "Eyedropper"
        PICK_AREA = "Pick Area"
        STOP = "Stop"
        COPY = "Copy"
        CROSS = "Cross"
        MUTE = "Mute"
        ZOOM_IN = "Zoom In"
        ZOOM_OUT = "Zoom Out"

        def __call__(self, _deco_cls: Type[T]) -> Type[T]:
            """
            Decorator method that adds the DEPENDS_ON_CURSOR flag and sets the cursor type.
            
            Args:
                ``_deco_cls``: The class being decorated
                
            Returns:
                The decorated class with cursor dependencies added
            """
            return OperatorOptionsDecorators._decorator(
                OperatorTypeFlags.DEPENDS_ON_CURSOR,
                bl_cursor_pending=self.name
            )(_deco_cls)
