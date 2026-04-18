from .btype_tool import BType_WorkSpaceToolTypes, BType_WorkSpaceTool
from .multi.btype_tool_multi import BType_WorkSpaceToolMulti
from .all_in_one.btype_tool_allinone import BType_WorkSpaceTool_AllInOne


class BType_TOOL:
    TOOL = BType_WorkSpaceToolTypes

    MultiToolGroup = BType_WorkSpaceToolMulti
    MultiTool = BType_WorkSpaceToolMulti.Tool
    AllInOneTool = BType_WorkSpaceTool_AllInOne
