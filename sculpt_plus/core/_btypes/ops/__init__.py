from .btype_op_base import BType_Operator
from .btype_op_action import BType_OpAction
from .btype_op_modal import BType_OpModal
from .btype_op_macro import MacroCreator



class BType_OPS:
    BASE = BType_Operator
    ACTION = BType_OpAction
    MODAL = BType_OpModal
    
    MacroCreator = MacroCreator
