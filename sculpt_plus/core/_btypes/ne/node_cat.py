import bpy
from dataclasses import dataclass
from typing import Dict, List, Type
from .node import BType_Node

@dataclass
class NodeCategory:
    name: str
    nodes: List[Type[BType_Node]]

_categories: Dict[str, Dict[str, NodeCategory]] = {}
