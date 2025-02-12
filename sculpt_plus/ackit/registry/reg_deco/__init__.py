from .handlers import Handlers as RegisterHandler
from .keymaps import RegisterKeymap
from .rna_sub import subscribe_to_rna_change as SubscribeToRNAChange, subscribe_to_rna_change_based_on_context as SubscribeToRNAContextChange
from .timer import new_timer_as_decorator as RegisterTimer
from .property_group import *
from .ui import *

class RegDeco:
    # PROP_GROUP = PropertyGroupRegister
    KEYMAP = RegisterKeymap
    RNA_SUB = SubscribeToRNAChange
    RNA_SUB_CONTEXT = SubscribeToRNAContextChange
    TIMER = RegisterTimer
    HANDLER = RegisterHandler
