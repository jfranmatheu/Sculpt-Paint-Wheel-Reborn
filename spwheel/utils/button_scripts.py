"""Python scripts for custom buttons.

Each script lives in the add-on user data (``<USER>/<addon id>/scripts/<script_id>.py``), next to
``preferences.json``, so buttons and their scripts are shared by every project. The button only
stores the ``script_id``.

Editing happens in a Blender Text datablock. The link between a Text and a script is kept for the
current session only: a Text saved inside a .blend could be stale (the script may have been edited
from another project), so it must never overwrite the file just because it exists.
"""

from __future__ import annotations

import re
import traceback
import uuid
from pathlib import Path

import bpy
from bpy.app.handlers import persistent

from ..core.globals import PATHS


SCRIPTS_DIR: Path = PATHS.USER_DATA / "scripts"
TEXT_KEY = "spwheel_script_id"
_SCRIPT_ID_RE = re.compile(r"[0-9a-f]{8,64}")

SCRIPT_TEMPLATE = '''\
# Sculpt+Paint Wheel custom button script.
# Runs when the button is clicked in the wheel.
# Available names: bpy, context (also C), D (bpy.data), button (this custom button).

import bpy

obj = context.active_object
print("Hello from", button.name, "on", obj.name if obj else None)
'''

# script_id -> Text name, for Texts opened for editing in this session.
_session_texts: dict[str, str] = {}


def new_script_id() -> str:
    return uuid.uuid4().hex


def is_valid_script_id(script_id: str) -> bool:
    return bool(script_id) and _SCRIPT_ID_RE.fullmatch(script_id) is not None


def script_path(script_id: str) -> Path | None:
    if not is_valid_script_id(script_id):
        return None
    return SCRIPTS_DIR / f"{script_id}.py"


def read_script(script_id: str) -> str | None:
    path = script_path(script_id)
    if path is None or not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def write_script(script_id: str, source: str) -> Path:
    path = script_path(script_id)
    if path is None:
        raise ValueError(f"Invalid script id: {script_id!r}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def delete_script(script_id: str) -> None:
    path = script_path(script_id)
    if path is not None and path.is_file():
        try:
            path.unlink()
        except OSError:
            pass
    _session_texts.pop(script_id, None)


# ---------------------------------------------------------------------------
# Text datablocks.
# ---------------------------------------------------------------------------

def get_linked_text(script_id: str) -> bpy.types.Text | None:
    """The Text opened for this script in this session, if it still exists."""
    name = _session_texts.get(script_id)
    if name is None:
        return None
    text = bpy.data.texts.get(name)
    if text is None or text.get(TEXT_KEY) != script_id:
        _session_texts.pop(script_id, None)
        return None
    return text


def get_text_script_id(text: bpy.types.Text | None) -> str | None:
    """Script id of a Text linked in this session (None for unlinked or stale Texts)."""
    if text is None:
        return None
    script_id = text.get(TEXT_KEY)
    if not isinstance(script_id, str) or get_linked_text(script_id) != text:
        return None
    return script_id


def open_text(script_id: str, button_name: str, fallback_source: str = "") -> bpy.types.Text:
    """Get (or create) the Text that edits this script, loaded from the script file."""
    if text := get_linked_text(script_id):
        return text
    source = read_script(script_id)
    if source is None:
        source = fallback_source
    text = bpy.data.texts.new(f"SPW_{button_name or 'Button'}.py")
    text.from_string(source)
    text[TEXT_KEY] = script_id
    text.use_fake_user = False
    _session_texts[script_id] = text.name
    return text


def save_text(text: bpy.types.Text) -> Path | None:
    script_id = get_text_script_id(text)
    if script_id is None:
        return None
    return write_script(script_id, text.as_string())


def show_text_in_editor(context: bpy.types.Context, text: bpy.types.Text) -> bool:
    """Show the Text in a Text Editor: an existing one if any, else a new window."""
    wm = context.window_manager
    for window in wm.windows:
        for area in window.screen.areas:
            if area.type == 'TEXT_EDITOR':
                area.spaces.active.text = text
                area.tag_redraw()
                return True
    try:
        old_windows = set(wm.windows[:])
        bpy.ops.wm.window_new()
        new_windows = [w for w in wm.windows if w not in old_windows]
        if not new_windows:
            return False
        area = max(new_windows[0].screen.areas, key=lambda a: a.width * a.height)
        area.type = 'TEXT_EDITOR'
        area.spaces.active.text = text
        return True
    except Exception:
        traceback.print_exc()
        return False


# ---------------------------------------------------------------------------
# Running.
# ---------------------------------------------------------------------------

def get_button_source(button) -> tuple[str | None, str]:
    """(source, filename) for a script button. Prefers the Text being edited in this session."""
    script_id = button.script_id
    if script_id:
        if text := get_linked_text(script_id):
            source = text.as_string()
            # Keep the file in sync with what is being tried in the wheel.
            try:
                write_script(script_id, source)
            except OSError:
                traceback.print_exc()
            return source, text.name
        path = script_path(script_id)
        return read_script(script_id), str(path) if path else "<spwheel script>"
    # Legacy / bundled defaults: source stored in the button itself.
    return (button.script_inline or None), f"<spwheel inline: {button.name}>"


def run_button_script(button, context: bpy.types.Context) -> str | None:
    """Run the button's script. Returns an error message, or None on success."""
    source, filename = get_button_source(button)
    if source is None:
        return f"Script for '{button.name}' not found"
    namespace = {
        "__name__": "__main__",
        "__file__": filename,
        "bpy": bpy,
        "context": context,
        "C": context,
        "D": bpy.data,
        "button": button,
    }
    try:
        exec(compile(source, filename, "exec"), namespace)
    except Exception as ex:
        traceback.print_exc()
        return f"{type(ex).__name__}: {ex}"
    try:
        bpy.ops.ed.undo_push(message=f"Script: {button.name}")
    except Exception:
        pass
    return None


def report_script_error(context: bpy.types.Context, title: str, message: str) -> None:
    def draw(menu, _context):
        for line in message.splitlines() or [message]:
            menu.layout.label(text=line)
        menu.layout.label(text="See the system console for the full traceback.", icon='CONSOLE')
    try:
        context.window_manager.popup_menu(draw, title=title, icon='ERROR')
    except Exception:
        print(f"[SPWheel] {title}: {message}")


# ---------------------------------------------------------------------------
# References (to delete scripts nobody uses).
# ---------------------------------------------------------------------------

def iter_all_buttons(context: bpy.types.Context):
    from ..pg.pg_wheel_storage import WheelStorage
    root = WheelStorage.get(context)
    if root is None:
        return
    for prop in root.bl_rna.properties:
        if prop.type != 'POINTER':
            continue
        storage = getattr(root, prop.identifier, None)
        for tarta_set in getattr(storage, "tarta_sets", ()):
            yield from tarta_set.buttons


def delete_script_if_unused(context: bpy.types.Context, script_id: str, ignore=None) -> None:
    if not is_valid_script_id(script_id):
        return
    for button in iter_all_buttons(context):
        if ignore is not None and button == ignore:
            continue
        if button.script_id == script_id:
            return
    delete_script(script_id)


@persistent
def _on_load_post(*_args):
    # Texts from the newly loaded file are not linked to any script.
    _session_texts.clear()


def register():
    if _on_load_post not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_on_load_post)


def unregister():
    if _on_load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_on_load_post)
