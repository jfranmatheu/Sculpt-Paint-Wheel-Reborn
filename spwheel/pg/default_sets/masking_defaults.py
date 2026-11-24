"""Second default custom-button set for Sculpt, "Masking": mask and face-set operators only."""

from ._buttons import operator as _op

MASKING_SET_NAME = "Masking"


def_sculpt_masking_buttons = (
    _op("Invert Mask", "mask_invert.png", "paint.mask_flood_fill#mode='INVERT'"),
    _op("Clear Mask", "mask_clear.png", "paint.mask_flood_fill#mode='VALUE', value=0"),
    _op("Smooth Mask", "mask_smooth.png", "sculpt.mask_filter#filter_type='SMOOTH', auto_iteration_count=True"),
    _op("Sharpen Mask", "mask_sharp.png", "sculpt.mask_filter#filter_type='SHARPEN', auto_iteration_count=True"),
    _op("Grow Mask", "mask_grow.png", "sculpt.mask_filter#filter_type='GROW', auto_iteration_count=True"),
    _op("Shrink Mask", "mask_shrink.png", "sculpt.mask_filter#filter_type='SHRINK', auto_iteration_count=True"),
    _op("Hide Masked", "hide.png", "paint.hide_show_masked#action='HIDE'"),
    _op("Show All", "show.png", "paint.hide_show_all#action='SHOW'"),
    _op("Invert Visible", "invert.png", "paint.visibility_invert"),
    _op("Face Set from Mask", "face_sets.png", "sculpt.face_sets_create#mode='MASKED'"),
)
