import time
from typing import Callable

from .globals import GLOBALS


DEBUG_BUFFER = []
DEBUG_BUFFER_ENABLED = False
_last_indent = 0


def enable_debug_buffer():
    global DEBUG_BUFFER_ENABLED
    DEBUG_BUFFER_ENABLED = True

def disable_debug_buffer():
    global DEBUG_BUFFER_ENABLED
    DEBUG_BUFFER_ENABLED = False

def print_debug_buffer():
    global DEBUG_BUFFER, DEBUG_BUFFER_ENABLED
    if DEBUG_BUFFER_ENABLED:
        if DEBUG_BUFFER:
            print_debug("\n".join(DEBUG_BUFFER))
            DEBUG_BUFFER.clear()
    '''    else:
            print_debug("DEBUG_BUFFER is empty.")
    else:
        print_debug("DEBUG_BUFFER_ENABLED is False.")'''


class CM_PrintDebugDeferred:
    def __init__(self):
        enable_debug_buffer()
    def print_bypass(self, *args, indent=0):
        global DEBUG_BUFFER_ENABLED
        DEBUG_BUFFER_ENABLED = False
        print_debug(*args, indent=indent)
        DEBUG_BUFFER_ENABLED = True
    def __enter__(self):
        return self.print_bypass
    def __exit__(self, exc_type, exc_val, exc_tb):
        disable_debug_buffer()
        print_debug_buffer()


def print_debug(*args, indent=0):
    """
    Print debug message with indentation.
    :param args: Message to print.
    :param indent: Indentation level. -1 to use last indentation level + 1.
    """
    if not GLOBALS.IN_DEVELOPMENT:
        return
    global DEBUG_BUFFER_ENABLED, DEBUG_BUFFER
    global _last_indent
    if indent == -1:
        indent = _last_indent + 1
    else:
        _last_indent = indent
        if indent == 0:
            if DEBUG_BUFFER_ENABLED:
                DEBUG_BUFFER.append("\n")
            else:
                print("\n")
    if DEBUG_BUFFER_ENABLED:
        DEBUG_BUFFER.append(f"{GLOBALS.ADDON.ID_UPPER}:" if indent == 0 else "    " * indent + " ".join(map(str, args)))
    else:
        print(f"{GLOBALS.ADDON.ID_UPPER}:" if indent == 0 else "", "    " * indent, *args)


class CM_PrintDebug:
    active_debuggers = []
    last_debugger = None

    def __init__(self, label: str = ""):
        self.indent = len(CM_PrintDebug.active_debuggers)
        if label:
            self.print(label)

    def print(self, msg: str):
        print_debug(msg, indent=self.indent)

    def __enter__(self) -> Callable[[str], None]:
        CM_PrintDebug.active_debuggers.append(self)
        CM_PrintDebug.last_debugger = self
        return self.print

    def __exit__(self, exc_type, exc_val, exc_tb):
        CM_PrintDebug.active_debuggers.remove(self)
        CM_PrintDebug.last_debugger = CM_PrintDebug.active_debuggers[-1] if CM_PrintDebug.active_debuggers else None


class PrintDebug:
    def __init__(self, label: str = ""):
        self.indent = len(CM_PrintDebug.active_debuggers)
        CM_PrintDebug.active_debuggers.append(self)
        CM_PrintDebug.last_debugger = self
        if label:
            self.print(label)

    def print(self, msg: str):
        print_debug(msg, indent=self.indent)

    def __del__(self):
        CM_PrintDebug.active_debuggers.remove(self)
        CM_PrintDebug.last_debugger = CM_PrintDebug.active_debuggers[-1] if CM_PrintDebug.active_debuggers else None


def time_it(fn):
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = fn(*args, **kwargs)
        end_time = time.perf_counter()
        print_debug(f"Time elapsed: %.6f sec" % (end_time - start_time))
        return result
    return wrapper


class CM_TimeIt:
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = time.perf_counter()
        print_debug(f"Time elapsed: %.6f sec" % (end_time - self.start_time))
        return False
