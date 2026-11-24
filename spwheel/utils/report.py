import bpy


def report_error(context: bpy.types.Context, title: str, message: str) -> None:
    """Show an error popup (e.g. a custom button that can't run); the console gets it if there's no window."""
    def draw(menu, _context):
        for line in message.splitlines() or [message]:
            menu.layout.label(text=line)
    print(f"[SPWheel] {title}: {message}")
    try:
        context.window_manager.popup_menu(draw, title=title, icon='ERROR')
    except Exception:
        pass
