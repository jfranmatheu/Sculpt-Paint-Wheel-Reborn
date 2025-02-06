from ._globals import GLOBALS
import pprint


def print_debug(*args) -> None:
    if GLOBALS.check_in_development():
        print(f'[{GLOBALS.ADDON_MODULE_UPPER}]', *args)


def pprint_debug(title: str, d: dict, sort: bool = False) -> None:
    if GLOBALS.check_in_development():
        print_debug('\n+++', title, '++++++++++++++++++++++++++++++++')
        pprint.pprint(d, indent=4, sort_dicts=sort)
        print_debug('++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++\n')


class CM_PrintDebug:
    def __init__(self, title: str) -> None:
        self.use_debug = GLOBALS.check_in_development()
        if self.use_debug:
            self.title = title
            print(f"<{GLOBALS.ADDON_MODULE_UPPER} - {title}>")

    def __enter__(self):
        def print_indent(msg: str, indent: int = 1, prefix: str = '>'):
            if self.use_debug:
                t_char = '\t'
                print(f"{''.join([t_char for i in range(indent)])}{prefix} {msg}")
        return print_indent

    def __exit__(self, exc_type, exc_value, trace):
        if self.use_debug:
            print(f"</{GLOBALS.ADDON_MODULE_UPPER} - {self.title}>")
