from .output import print_debug, pprint_debug, DebugPrintContext
from .logger import get_logger
from .profiler import (
    profile_function,
    profile_block,
    start_timer,
    stop_timer
)

# Alias for better clarity!
debug_context = DebugPrintContext

__all__ = [
    'print_debug',
    'pprint_debug',
    'debug_context',
    'get_logger',
    'profile_function',
    'profile_block',
    'start_timer',
    'stop_timer'
]


''' Usage Examples:

from ackit.debug import get_logger, profile_function, profile_block, start_timer, stop_timer

# Using the logger
logger = get_logger()
logger.info("Starting operation")
logger.debug("Detailed debug info")
logger.error("Something went wrong", exc_info=True)

# Using the profiler decorator
@profile_function(output_file="my_profile_results.prof")
def expensive_function():
    # Some expensive operations
    pass

# Using the profiler context manager
with profile_block("Critical Section"):
    # Code to profile
    pass

# Using simple timers
start_timer("operation")
# Do something
elapsed = stop_timer("operation")

'''
