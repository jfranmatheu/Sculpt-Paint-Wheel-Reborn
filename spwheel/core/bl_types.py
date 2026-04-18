"""Interface for _btypes module."""
from ._btypes import (
    BType_AddonPreferences as AddonPreferences,
    BType_UI as _ui,
    BType_OPS as _ops,
    BType_PROP_GROUP as _pg,
    BType_TOOL as _tools,
    BType_GIZMOS as _gz,
)
# Data.
PropertyGroupRoot = _pg.ROOT
PropertyGroup = _pg.CHILD
# UI.
PanelPopover = _ui.PANEL_POPOVER
Panel = _ui.PANEL.CUSTOM
PanelPresets = _ui.PANEL
PanelTypes = PanelPresets # ALIAS.
Menu = _ui.MENU
MenuPie = _ui.MENU_PIE
UIList = _ui.UI_LIST
# Operators.
Operator = _ops.BASE
OperatorAction = _ops.ACTION
OperatorModal = _ops.MODAL
# Macros.
MacroCreator = _ops.MacroCreator
# Tools.
Tool = _tools.TOOL.CUSTOM
ToolPresets = _tools.TOOL
ToolTypes = ToolPresets # ALIAS.
MultiToolGroup = _tools.MultiToolGroup
MultiTool = _tools.MultiTool
AllInOneTool = _tools.AllInOneTool
# Gizmos.
ToolWidget = _gz.TOOL_WIDGET
Gizmo = _gz.GZ
GizmoGroup = _gz.GZG
