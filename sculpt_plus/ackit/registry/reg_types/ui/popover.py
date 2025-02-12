from .panel import Panel
from ...flags import PanelOptions


class Popover(Panel):
    bl_options: set[str] = {PanelOptions.INSTANCED.name}
