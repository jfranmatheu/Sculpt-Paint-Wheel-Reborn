from bpy.props import BoolProperty
from bpy.types import UILayout

from ...core.bl_types import UIList


class TartaSetList(UIList):
    # Custom properties, saved with .blend file.
    use_filter_empty: BoolProperty(
        name="Filter Empty",
        default=False,
        options=set(),
        description="Whether to filter empty vertex groups",
    )
    use_filter_empty_reverse: BoolProperty(
        name="Reverse Empty",
        default=False,
        options=set(),
        description="Reverse empty filtering",
    )
    use_filter_name_reverse: BoolProperty(
        name="Reverse Name",
        default=False,
        options=set(),
        description="Reverse name filtering",
    )
    use_filter_show : BoolProperty(
        name="Show Filters",
        default=False,
        options=set(),
        description="Show filtering options",
    )

    # The draw_item function is called for each item of the collection that is visible in the list.
    #   data is the RNA object containing the collection,
    #   item is the current drawn item of the collection,
    #   icon is the "computed" icon for the item (as an integer, because some objects like materials or textures
    #   have custom icons ID, which are not available as enum items).
    #   active_data is the RNA object containing the active property for the collection (i.e. integer pointing to the
    #   active item of the collection).
    #   active_propname is the name of the active property (use 'getattr(active_data, active_propname)').
    #   index is index of the current item in the collection.
    #   flt_flag is the result of the filtering process for this item.
    #   Note: as index and flt_flag are optional arguments, you do not have to use/declare them here if you don't
    #         need them.
    def draw_item(self, context, layout: UILayout, data, item, icon, active_data, active_propname, index):
        # data == wheel prefs
        # item == custom button set

        # You should always start your row layout by a label (icon + text), or a non-embossed text field,
        # this will also make the row easily selectable in the list! The later also enables ctrl-click rename.
        # We use icon_value of label, as our given icon is an integer value, not an enum ID.
        # Note "data" names should never be translated!
        # is_active = index == getattr(active_data, active_propname)
        # if is_active:
        #     sub = layout.column(align=True)
        # else:
        #     sub = layout.row(align=True)
        row = layout.row(align=True)
        row.prop(item, 'name', icon='OUTLINER_COLLECTION')
        # sub = row.row(align=True)
        # sub.operator() # delete
