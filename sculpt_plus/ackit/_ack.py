from enum import Enum, auto
from typing import Callable, Type

from .registry.reg_types import *
from .registry.reg_deco import *
from .registry.flags import *
from .registry.props import *
from .enums import *
from .registry.polling import *

__all__ = [
    'ACK',
]


class ACK:
    class Types:
        class Ops:
            Generic = Operator
            Action = Action
            Modal = Modal
            
        class UI:
            Panel = Panel
            Menu = Menu
            PieMenu = PieMenu
            Popover = Popover
            UIList = UIList
            
        class Data:
            AddonPreferences = AddonPreferences
            PropertyGroup = PropertyGroup
        
        # Event = FakeEvent
        # EventType = EventType
        # EventValue = EventValue

    class Returns:
        Operator = OpsReturn
        Submodal = SubmodalReturn

    class Props:
        Typed = TypedProperty
        Wrapped = wrapped

    class FromFunction:
        ACTION = Action.from_function
        PANEL = PanelFromFunction
        MENU = Menu.from_function
        PIE_MENU = PieMenu.from_function
        POPOVER = Popover.from_function
    
    class Flags:
        OPERATOR = OperatorOptions
        MODAL = ModalFlags
        PANEL = PanelOptions
    
    Poll = Polling
