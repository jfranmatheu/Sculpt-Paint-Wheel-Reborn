from mathutils import Vector
from bpy.types import Event


EVENT_TYPE = 'NONE'
EVENT_VALUE = 'NONE'
EVENT_MODIFIERS = { # Ctrl, Shift, Alt states.
    'ctrl':     False,
    'shift':    False,
    'alt':      False
}
MOUSE = Vector((0, 0))
MOUSE_REGION = Vector((0, 0))

def set_global_event(event: Event):
    global EVENT_TYPE
    global EVENT_VALUE
    global EVENT_MODIFIERS
    EVENT_TYPE = event.type
    EVENT_VALUE = event.value
    EVENT_MODIFIERS['alt'] = event.alt
    EVENT_MODIFIERS['ctrl'] = event.ctrl
    EVENT_MODIFIERS['shift'] = event.shift
    global MOUSE
    global MOUSE_REGION
    MOUSE = Vector((event.mouse_x, event.mouse_y))
    MOUSE_REGION = Vector((event.mouse_region_x, event.mouse_region_y))

def get_global_event() -> tuple[str, str]:
    global EVENT_TYPE
    global EVENT_VALUE
    return EVENT_TYPE, EVENT_VALUE


class _isEventValue:
    _ANY: str = 'ANY'
    @property
    def ANY(self) -> bool: global EVENT_VALUE; return EVENT_VALUE == 'ANY'

    _PRESS: str = 'PRESS'
    @property
    def PRESS(self) -> bool: global EVENT_VALUE; return EVENT_VALUE == 'PRESS'

    _RELEASE: str = 'RELEASE'
    @property
    def RELEASE(self) -> bool: global EVENT_VALUE; return EVENT_VALUE == 'RELEASE'

    _CLICK: str = 'CLICK'
    @property
    def CLICK(self) -> bool: global EVENT_VALUE; return EVENT_VALUE == 'CLICK'

    _DOUBLE_CLICK: str = 'DOUBLE_CLICK'
    @property
    def DOUBLE_CLICK(self) -> bool: global EVENT_VALUE; return EVENT_VALUE == 'DOUBLE_CLICK'

    _CLICK_DRAG: str = 'CLICK_DRAG'
    @property
    def CLICK_DRAG(self) -> bool: global EVENT_VALUE; return EVENT_VALUE == 'CLICK_DRAG'

    _NOTHING: str = 'NOTHING'
    @property
    def NOTHING(self) -> bool: global EVENT_VALUE; return EVENT_VALUE == 'NOTHING'


class _isEventType:
    _NONE: str = 'NONE'
    @property
    def NONE(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NONE'

    _LEFTMOUSE: str = 'LEFTMOUSE'
    @property
    def LEFTMOUSE(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'LEFTMOUSE'

    _MIDDLEMOUSE: str = 'MIDDLEMOUSE'
    @property
    def MIDDLEMOUSE(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'MIDDLEMOUSE'

    _RIGHTMOUSE: str = 'RIGHTMOUSE'
    @property
    def RIGHTMOUSE(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'RIGHTMOUSE'

    _BUTTON4MOUSE: str = 'BUTTON4MOUSE'
    @property
    def BUTTON4MOUSE(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'BUTTON4MOUSE'

    _BUTTON5MOUSE: str = 'BUTTON5MOUSE'
    @property
    def BUTTON5MOUSE(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'BUTTON5MOUSE'

    _BUTTON6MOUSE: str = 'BUTTON6MOUSE'
    @property
    def BUTTON6MOUSE(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'BUTTON6MOUSE'

    _BUTTON7MOUSE: str = 'BUTTON7MOUSE'
    @property
    def BUTTON7MOUSE(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'BUTTON7MOUSE'

    _PEN: str = 'PEN'
    @property
    def PEN(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'PEN'

    _ERASER: str = 'ERASER'
    @property
    def ERASER(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'ERASER'

    _MOUSEMOVE: str = 'MOUSEMOVE'
    @property
    def MOUSEMOVE(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'MOUSEMOVE'

    _INBETWEEN_MOUSEMOVE: str = 'INBETWEEN_MOUSEMOVE'
    @property
    def INBETWEEN_MOUSEMOVE(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'INBETWEEN_MOUSEMOVE'

    _TRACKPADPAN: str = 'TRACKPADPAN'
    @property
    def TRACKPADPAN(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'TRACKPADPAN'

    _TRACKPADZOOM: str = 'TRACKPADZOOM'
    @property
    def TRACKPADZOOM(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'TRACKPADZOOM'

    _MOUSEROTATE: str = 'MOUSEROTATE'
    @property
    def MOUSEROTATE(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'MOUSEROTATE'

    _MOUSESMARTZOOM: str = 'MOUSESMARTZOOM'
    @property
    def MOUSESMARTZOOM(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'MOUSESMARTZOOM'

    _WHEELUPMOUSE: str = 'WHEELUPMOUSE'
    @property
    def WHEELUPMOUSE(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'WHEELUPMOUSE'

    _WHEELDOWNMOUSE: str = 'WHEELDOWNMOUSE'
    @property
    def WHEELDOWNMOUSE(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'WHEELDOWNMOUSE'

    _WHEELINMOUSE: str = 'WHEELINMOUSE'
    @property
    def WHEELINMOUSE(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'WHEELINMOUSE'

    _WHEELOUTMOUSE: str = 'WHEELOUTMOUSE'
    @property
    def WHEELOUTMOUSE(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'WHEELOUTMOUSE'

    _A: str = 'A'
    @property
    def A(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'A'

    _B: str = 'B'
    @property
    def B(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'B'

    _C: str = 'C'
    @property
    def C(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'C'

    _D: str = 'D'
    @property
    def D(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'D'

    _E: str = 'E'
    @property
    def E(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'E'

    _F: str = 'F'
    @property
    def F(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'F'

    _G: str = 'G'
    @property
    def G(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'G'

    _H: str = 'H'
    @property
    def H(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'H'

    _I: str = 'I'
    @property
    def I(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'I'

    _J: str = 'J'
    @property
    def J(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'J'

    _K: str = 'K'
    @property
    def K(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'K'

    _L: str = 'L'
    @property
    def L(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'L'

    _M: str = 'M'
    @property
    def M(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'M'

    _N: str = 'N'
    @property
    def N(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'N'

    _O: str = 'O'
    @property
    def O(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'O'

    _P: str = 'P'
    @property
    def P(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'P'

    _Q: str = 'Q'
    @property
    def Q(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'Q'

    _R: str = 'R'
    @property
    def R(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'R'

    _S: str = 'S'
    @property
    def S(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'S'

    _T: str = 'T'
    @property
    def T(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'T'

    _U: str = 'U'
    @property
    def U(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'U'

    _V: str = 'V'
    @property
    def V(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'V'

    _W: str = 'W'
    @property
    def W(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'W'

    _X: str = 'X'
    @property
    def X(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'X'

    _Y: str = 'Y'
    @property
    def Y(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'Y'

    _Z: str = 'Z'
    @property
    def Z(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'Z'

    _ZERO: str = 'ZERO'
    @property
    def ZERO(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'ZERO'

    _ONE: str = 'ONE'
    @property
    def ONE(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'ONE'

    _TWO: str = 'TWO'
    @property
    def TWO(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'TWO'

    _THREE: str = 'THREE'
    @property
    def THREE(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'THREE'

    _FOUR: str = 'FOUR'
    @property
    def FOUR(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'FOUR'

    _FIVE: str = 'FIVE'
    @property
    def FIVE(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'FIVE'

    _SIX: str = 'SIX'
    @property
    def SIX(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'SIX'

    _SEVEN: str = 'SEVEN'
    @property
    def SEVEN(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'SEVEN'

    _EIGHT: str = 'EIGHT'
    @property
    def EIGHT(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'EIGHT'

    _NINE: str = 'NINE'
    @property
    def NINE(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NINE'

    _LEFT_CTRL: str = 'LEFT_CTRL'
    @property
    def LEFT_CTRL(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'LEFT_CTRL'

    _LEFT_ALT: str = 'LEFT_ALT'
    @property
    def LEFT_ALT(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'LEFT_ALT'

    _LEFT_SHIFT: str = 'LEFT_SHIFT'
    @property
    def LEFT_SHIFT(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'LEFT_SHIFT'

    _RIGHT_ALT: str = 'RIGHT_ALT'
    @property
    def RIGHT_ALT(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'RIGHT_ALT'

    _RIGHT_CTRL: str = 'RIGHT_CTRL'
    @property
    def RIGHT_CTRL(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'RIGHT_CTRL'

    _RIGHT_SHIFT: str = 'RIGHT_SHIFT'
    @property
    def RIGHT_SHIFT(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'RIGHT_SHIFT'

    _OSKEY: str = 'OSKEY'
    @property
    def OSKEY(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'OSKEY'

    _APP: str = 'APP'
    @property
    def APP(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'APP'

    _GRLESS: str = 'GRLESS'
    @property
    def GRLESS(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'GRLESS'

    _ESC: str = 'ESC'
    @property
    def ESC(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'ESC'

    _TAB: str = 'TAB'
    @property
    def TAB(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'TAB'

    _RET: str = 'RET'
    @property
    def RET(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'RET'

    _SPACE: str = 'SPACE'
    @property
    def SPACE(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'SPACE'

    _LINE_FEED: str = 'LINE_FEED'
    @property
    def LINE_FEED(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'LINE_FEED'

    _BACK_SPACE: str = 'BACK_SPACE'
    @property
    def BACK_SPACE(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'BACK_SPACE'

    _DEL: str = 'DEL'
    @property
    def DEL(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'DEL'

    _SEMI_COLON: str = 'SEMI_COLON'
    @property
    def SEMI_COLON(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'SEMI_COLON'

    _PERIOD: str = 'PERIOD'
    @property
    def PERIOD(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'PERIOD'

    _COMMA: str = 'COMMA'
    @property
    def COMMA(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'COMMA'

    _QUOTE: str = 'QUOTE'
    @property
    def QUOTE(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'QUOTE'

    _ACCENT_GRAVE: str = 'ACCENT_GRAVE'
    @property
    def ACCENT_GRAVE(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'ACCENT_GRAVE'

    _MINUS: str = 'MINUS'
    @property
    def MINUS(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'MINUS'

    _PLUS: str = 'PLUS'
    @property
    def PLUS(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'PLUS'

    _SLASH: str = 'SLASH'
    @property
    def SLASH(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'SLASH'

    _BACK_SLASH: str = 'BACK_SLASH'
    @property
    def BACK_SLASH(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'BACK_SLASH'

    _EQUAL: str = 'EQUAL'
    @property
    def EQUAL(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'EQUAL'

    _LEFT_BRACKET: str = 'LEFT_BRACKET'
    @property
    def LEFT_BRACKET(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'LEFT_BRACKET'

    _RIGHT_BRACKET: str = 'RIGHT_BRACKET'
    @property
    def RIGHT_BRACKET(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'RIGHT_BRACKET'

    _LEFT_ARROW: str = 'LEFT_ARROW'
    @property
    def LEFT_ARROW(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'LEFT_ARROW'

    _DOWN_ARROW: str = 'DOWN_ARROW'
    @property
    def DOWN_ARROW(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'DOWN_ARROW'

    _RIGHT_ARROW: str = 'RIGHT_ARROW'
    @property
    def RIGHT_ARROW(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'RIGHT_ARROW'

    _UP_ARROW: str = 'UP_ARROW'
    @property
    def UP_ARROW(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'UP_ARROW'

    _NUMPAD_2: str = 'NUMPAD_2'
    @property
    def NUMPAD_2(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NUMPAD_2'

    _NUMPAD_4: str = 'NUMPAD_4'
    @property
    def NUMPAD_4(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NUMPAD_4'

    _NUMPAD_6: str = 'NUMPAD_6'
    @property
    def NUMPAD_6(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NUMPAD_6'

    _NUMPAD_8: str = 'NUMPAD_8'
    @property
    def NUMPAD_8(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NUMPAD_8'

    _NUMPAD_1: str = 'NUMPAD_1'
    @property
    def NUMPAD_1(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NUMPAD_1'

    _NUMPAD_3: str = 'NUMPAD_3'
    @property
    def NUMPAD_3(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NUMPAD_3'

    _NUMPAD_5: str = 'NUMPAD_5'
    @property
    def NUMPAD_5(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NUMPAD_5'

    _NUMPAD_7: str = 'NUMPAD_7'
    @property
    def NUMPAD_7(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NUMPAD_7'

    _NUMPAD_9: str = 'NUMPAD_9'
    @property
    def NUMPAD_9(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NUMPAD_9'

    _NUMPAD_PERIOD: str = 'NUMPAD_PERIOD'
    @property
    def NUMPAD_PERIOD(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NUMPAD_PERIOD'

    _NUMPAD_SLASH: str = 'NUMPAD_SLASH'
    @property
    def NUMPAD_SLASH(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NUMPAD_SLASH'

    _NUMPAD_ASTERIX: str = 'NUMPAD_ASTERIX'
    @property
    def NUMPAD_ASTERIX(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NUMPAD_ASTERIX'

    _NUMPAD_0: str = 'NUMPAD_0'
    @property
    def NUMPAD_0(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NUMPAD_0'

    _NUMPAD_MINUS: str = 'NUMPAD_MINUS'
    @property
    def NUMPAD_MINUS(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NUMPAD_MINUS'

    _NUMPAD_ENTER: str = 'NUMPAD_ENTER'
    @property
    def NUMPAD_ENTER(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NUMPAD_ENTER'

    _NUMPAD_PLUS: str = 'NUMPAD_PLUS'
    @property
    def NUMPAD_PLUS(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NUMPAD_PLUS'

    _F1: str = 'F1'
    @property
    def F1(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'F1'

    _F2: str = 'F2'
    @property
    def F2(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'F2'

    _F3: str = 'F3'
    @property
    def F3(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'F3'

    _F4: str = 'F4'
    @property
    def F4(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'F4'

    _F5: str = 'F5'
    @property
    def F5(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'F5'

    _F6: str = 'F6'
    @property
    def F6(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'F6'

    _F7: str = 'F7'
    @property
    def F7(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'F7'

    _F8: str = 'F8'
    @property
    def F8(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'F8'

    _F9: str = 'F9'
    @property
    def F9(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'F9'

    _F10: str = 'F10'
    @property
    def F10(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'F10'

    _F11: str = 'F11'
    @property
    def F11(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'F11'

    _F12: str = 'F12'
    @property
    def F12(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'F12'

    _F13: str = 'F13'
    @property
    def F13(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'F13'

    _F14: str = 'F14'
    @property
    def F14(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'F14'

    _F15: str = 'F15'
    @property
    def F15(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'F15'

    _F16: str = 'F16'
    @property
    def F16(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'F16'

    _F17: str = 'F17'
    @property
    def F17(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'F17'

    _F18: str = 'F18'
    @property
    def F18(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'F18'

    _F19: str = 'F19'
    @property
    def F19(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'F19'

    _F20: str = 'F20'
    @property
    def F20(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'F20'

    _F21: str = 'F21'
    @property
    def F21(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'F21'

    _F22: str = 'F22'
    @property
    def F22(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'F22'

    _F23: str = 'F23'
    @property
    def F23(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'F23'

    _F24: str = 'F24'
    @property
    def F24(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'F24'

    _PAUSE: str = 'PAUSE'
    @property
    def PAUSE(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'PAUSE'

    _INSERT: str = 'INSERT'
    @property
    def INSERT(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'INSERT'

    _HOME: str = 'HOME'
    @property
    def HOME(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'HOME'

    _PAGE_UP: str = 'PAGE_UP'
    @property
    def PAGE_UP(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'PAGE_UP'

    _PAGE_DOWN: str = 'PAGE_DOWN'
    @property
    def PAGE_DOWN(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'PAGE_DOWN'

    _END: str = 'END'
    @property
    def END(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'END'

    _MEDIA_PLAY: str = 'MEDIA_PLAY'
    @property
    def MEDIA_PLAY(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'MEDIA_PLAY'

    _MEDIA_STOP: str = 'MEDIA_STOP'
    @property
    def MEDIA_STOP(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'MEDIA_STOP'

    _MEDIA_FIRST: str = 'MEDIA_FIRST'
    @property
    def MEDIA_FIRST(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'MEDIA_FIRST'

    _MEDIA_LAST: str = 'MEDIA_LAST'
    @property
    def MEDIA_LAST(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'MEDIA_LAST'

    _TEXTINPUT: str = 'TEXTINPUT'
    @property
    def TEXTINPUT(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'TEXTINPUT'

    _WINDOW_DEACTIVATE: str = 'WINDOW_DEACTIVATE'
    @property
    def WINDOW_DEACTIVATE(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'WINDOW_DEACTIVATE'

    _TIMER: str = 'TIMER'
    @property
    def TIMER(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'TIMER'

    _TIMER0: str = 'TIMER0'
    @property
    def TIMER0(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'TIMER0'

    _TIMER1: str = 'TIMER1'
    @property
    def TIMER1(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'TIMER1'

    _TIMER2: str = 'TIMER2'
    @property
    def TIMER2(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'TIMER2'

    _TIMER_JOBS: str = 'TIMER_JOBS'
    @property
    def TIMER_JOBS(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'TIMER_JOBS'

    _TIMER_AUTOSAVE: str = 'TIMER_AUTOSAVE'
    @property
    def TIMER_AUTOSAVE(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'TIMER_AUTOSAVE'

    _TIMER_REPORT: str = 'TIMER_REPORT'
    @property
    def TIMER_REPORT(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'TIMER_REPORT'

    _TIMERREGION: str = 'TIMERREGION'
    @property
    def TIMERREGION(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'TIMERREGION'

    _NDOF_MOTION: str = 'NDOF_MOTION'
    @property
    def NDOF_MOTION(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NDOF_MOTION'

    _NDOF_BUTTON_MENU: str = 'NDOF_BUTTON_MENU'
    @property
    def NDOF_BUTTON_MENU(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NDOF_BUTTON_MENU'

    _NDOF_BUTTON_FIT: str = 'NDOF_BUTTON_FIT'
    @property
    def NDOF_BUTTON_FIT(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NDOF_BUTTON_FIT'

    _NDOF_BUTTON_TOP: str = 'NDOF_BUTTON_TOP'
    @property
    def NDOF_BUTTON_TOP(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NDOF_BUTTON_TOP'

    _NDOF_BUTTON_BOTTOM: str = 'NDOF_BUTTON_BOTTOM'
    @property
    def NDOF_BUTTON_BOTTOM(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NDOF_BUTTON_BOTTOM'

    _NDOF_BUTTON_LEFT: str = 'NDOF_BUTTON_LEFT'
    @property
    def NDOF_BUTTON_LEFT(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NDOF_BUTTON_LEFT'

    _NDOF_BUTTON_RIGHT: str = 'NDOF_BUTTON_RIGHT'
    @property
    def NDOF_BUTTON_RIGHT(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NDOF_BUTTON_RIGHT'

    _NDOF_BUTTON_FRONT: str = 'NDOF_BUTTON_FRONT'
    @property
    def NDOF_BUTTON_FRONT(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NDOF_BUTTON_FRONT'

    _NDOF_BUTTON_BACK: str = 'NDOF_BUTTON_BACK'
    @property
    def NDOF_BUTTON_BACK(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NDOF_BUTTON_BACK'

    _NDOF_BUTTON_ISO1: str = 'NDOF_BUTTON_ISO1'
    @property
    def NDOF_BUTTON_ISO1(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NDOF_BUTTON_ISO1'

    _NDOF_BUTTON_ISO2: str = 'NDOF_BUTTON_ISO2'
    @property
    def NDOF_BUTTON_ISO2(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NDOF_BUTTON_ISO2'

    _NDOF_BUTTON_ROLL_CW: str = 'NDOF_BUTTON_ROLL_CW'
    @property
    def NDOF_BUTTON_ROLL_CW(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NDOF_BUTTON_ROLL_CW'

    _NDOF_BUTTON_ROLL_CCW: str = 'NDOF_BUTTON_ROLL_CCW'
    @property
    def NDOF_BUTTON_ROLL_CCW(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NDOF_BUTTON_ROLL_CCW'

    _NDOF_BUTTON_SPIN_CW: str = 'NDOF_BUTTON_SPIN_CW'
    @property
    def NDOF_BUTTON_SPIN_CW(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NDOF_BUTTON_SPIN_CW'

    _NDOF_BUTTON_SPIN_CCW: str = 'NDOF_BUTTON_SPIN_CCW'
    @property
    def NDOF_BUTTON_SPIN_CCW(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NDOF_BUTTON_SPIN_CCW'

    _NDOF_BUTTON_TILT_CW: str = 'NDOF_BUTTON_TILT_CW'
    @property
    def NDOF_BUTTON_TILT_CW(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NDOF_BUTTON_TILT_CW'

    _NDOF_BUTTON_TILT_CCW: str = 'NDOF_BUTTON_TILT_CCW'
    @property
    def NDOF_BUTTON_TILT_CCW(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NDOF_BUTTON_TILT_CCW'

    _NDOF_BUTTON_ROTATE: str = 'NDOF_BUTTON_ROTATE'
    @property
    def NDOF_BUTTON_ROTATE(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NDOF_BUTTON_ROTATE'

    _NDOF_BUTTON_PANZOOM: str = 'NDOF_BUTTON_PANZOOM'
    @property
    def NDOF_BUTTON_PANZOOM(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NDOF_BUTTON_PANZOOM'

    _NDOF_BUTTON_DOMINANT: str = 'NDOF_BUTTON_DOMINANT'
    @property
    def NDOF_BUTTON_DOMINANT(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NDOF_BUTTON_DOMINANT'

    _NDOF_BUTTON_PLUS: str = 'NDOF_BUTTON_PLUS'
    @property
    def NDOF_BUTTON_PLUS(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NDOF_BUTTON_PLUS'

    _NDOF_BUTTON_MINUS: str = 'NDOF_BUTTON_MINUS'
    @property
    def NDOF_BUTTON_MINUS(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NDOF_BUTTON_MINUS'

    _NDOF_BUTTON_V1: str = 'NDOF_BUTTON_V1'
    @property
    def NDOF_BUTTON_V1(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NDOF_BUTTON_V1'

    _NDOF_BUTTON_V2: str = 'NDOF_BUTTON_V2'
    @property
    def NDOF_BUTTON_V2(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NDOF_BUTTON_V2'

    _NDOF_BUTTON_V3: str = 'NDOF_BUTTON_V3'
    @property
    def NDOF_BUTTON_V3(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NDOF_BUTTON_V3'

    _NDOF_BUTTON_1: str = 'NDOF_BUTTON_1'
    @property
    def NDOF_BUTTON_1(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NDOF_BUTTON_1'

    _NDOF_BUTTON_2: str = 'NDOF_BUTTON_2'
    @property
    def NDOF_BUTTON_2(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NDOF_BUTTON_2'

    _NDOF_BUTTON_3: str = 'NDOF_BUTTON_3'
    @property
    def NDOF_BUTTON_3(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NDOF_BUTTON_3'

    _NDOF_BUTTON_4: str = 'NDOF_BUTTON_4'
    @property
    def NDOF_BUTTON_4(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NDOF_BUTTON_4'

    _NDOF_BUTTON_5: str = 'NDOF_BUTTON_5'
    @property
    def NDOF_BUTTON_5(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NDOF_BUTTON_5'

    _NDOF_BUTTON_6: str = 'NDOF_BUTTON_6'
    @property
    def NDOF_BUTTON_6(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NDOF_BUTTON_6'

    _NDOF_BUTTON_7: str = 'NDOF_BUTTON_7'
    @property
    def NDOF_BUTTON_7(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NDOF_BUTTON_7'

    _NDOF_BUTTON_8: str = 'NDOF_BUTTON_8'
    @property
    def NDOF_BUTTON_8(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NDOF_BUTTON_8'

    _NDOF_BUTTON_9: str = 'NDOF_BUTTON_9'
    @property
    def NDOF_BUTTON_9(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NDOF_BUTTON_9'

    _NDOF_BUTTON_10: str = 'NDOF_BUTTON_10'
    @property
    def NDOF_BUTTON_10(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NDOF_BUTTON_10'

    _NDOF_BUTTON_A: str = 'NDOF_BUTTON_A'
    @property
    def NDOF_BUTTON_A(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NDOF_BUTTON_A'

    _NDOF_BUTTON_B: str = 'NDOF_BUTTON_B'
    @property
    def NDOF_BUTTON_B(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NDOF_BUTTON_B'

    _NDOF_BUTTON_C: str = 'NDOF_BUTTON_C'
    @property
    def NDOF_BUTTON_C(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'NDOF_BUTTON_C'

    _ACTIONZONE_AREA: str = 'ACTIONZONE_AREA'
    @property
    def ACTIONZONE_AREA(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'ACTIONZONE_AREA'

    _ACTIONZONE_REGION: str = 'ACTIONZONE_REGION'
    @property
    def ACTIONZONE_REGION(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'ACTIONZONE_REGION'

    _ACTIONZONE_FULLSCREEN: str = 'ACTIONZONE_FULLSCREEN'
    @property
    def ACTIONZONE_FULLSCREEN(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'ACTIONZONE_FULLSCREEN'

    _XR_ACTION: str = 'XR_ACTION'
    @property
    def XR_ACTION(self) -> bool: global EVENT_TYPE; return EVENT_TYPE == 'XR_ACTION'


IsEventValue = _isEventValue()
IsEventType  = _isEventType()


class GEvent:
    TYPE = _isEventType
    VALUE = _isEventValue

    @staticmethod
    def get_mouse_window_pos() -> Vector:
        global MOUSE
        return MOUSE.copy()

    @staticmethod
    def get_mouse_region_pos() -> Vector:
        global MOUSE_REGION
        return MOUSE_REGION.copy()

    @staticmethod
    def check(event_type: str, event_value: str, shift: bool = None, alt: bool = None, ctrl: bool = None) -> bool:
        global EVENT_TYPE
        global EVENT_VALUE
        global EVENT_MODIFIERS
        if shift is not None and EVENT_MODIFIERS['shift'] != shift:
            return False
        if alt is not None and EVENT_MODIFIERS['alt'] != alt:
            return False
        if ctrl is not None and EVENT_MODIFIERS['ctrl'] != ctrl:
            return False
        if event_value == 'ANY':
            return event_type == EVENT_TYPE
        return event_type == EVENT_TYPE and event_value == EVENT_VALUE

is_event = GEvent.check
