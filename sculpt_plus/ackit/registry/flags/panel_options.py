from enum import Enum, auto


class PanelOptions(Enum):
    ''' Use as decorator over a Panel subclass. '''
    HIDE_HEADER = auto()
    DEFAULT_CLOSED = auto()
    INSTANCED = auto()

    def __call__(self, panel_cls):
        if not hasattr(panel_cls, 'bl_options') or panel_cls.bl_options is None:
            panel_cls.bl_options = set()
        panel_cls.bl_options.add(self.name)
        return panel_cls
