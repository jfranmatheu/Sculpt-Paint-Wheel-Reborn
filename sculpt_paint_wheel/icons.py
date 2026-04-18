# /icons.py
# Code automatically generated!
from pathlib import Path
from .core._auto_code.icons import IconsEnum, IconsViewer

icons_dirpath = Path(".")


class Icons(IconsViewer):

	class MAIN(IconsEnum):
		ARROW_DOWN = icons_dirpath / "arrow_down.png"
		ARROW_UP = icons_dirpath / "arrow_up.png"
		BLUE_BUTTON = icons_dirpath / "blue_button.png"

