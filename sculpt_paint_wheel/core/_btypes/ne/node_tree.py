import bpy
from typing import Type
from .._base import BType

class BType_NodeTree(BType, bpy.types.NodeTree):

    @classmethod
    def add_node(cls: Type['BType_NodeTree'], category: str = "General"):
        def decorator(node_cls):
            node_cls._node_tree_cls = cls
            node_cls._node_category_name = category
            @classmethod
            def poll(ncls, ntree):
                return ntree.bl_idname == cls.bl_idname
            node_cls.poll = poll
            return node_cls
        return decorator
