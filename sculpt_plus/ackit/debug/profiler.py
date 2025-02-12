import time
import cProfile
import pstats
from pathlib import Path
from typing import Optional, Callable, Any, Union
from functools import wraps

from ..globals import GLOBALS
from .logger import get_logger


class AddonProfiler:
    """
    Profiling utility for Blender addons that can profile functions and code blocks.
    Supports both simple timing and detailed cProfile analysis.
    """

    def __init__(self):
        self.logger = get_logger()
        self.profiler = cProfile.Profile()
        self._active_timers = {}

    def start_timer(self, name: str):
        """Start a named timer."""
        self._active_timers[name] = time.time()

    def stop_timer(self, name: str) -> float:
        """Stop a named timer and return elapsed time."""
        if name not in self._active_timers:
            self.logger.warning(f"Timer '{name}' was never started")
            return 0.0

        elapsed = time.time() - self._active_timers.pop(name)
        self.logger.debug(f"Timer '{name}' elapsed: {elapsed:.4f} seconds")
        return elapsed

    def profile_function(self, output_file: Optional[Union[str, Path]] = None):
        """
        Decorator to profile a function using cProfile.

        Args:
            output_file: Optional file path to save profiling results.
                        If None, results are printed to console.
        """

        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                self.profiler.enable()
                try:
                    result = func(*args, **kwargs)
                finally:
                    self.profiler.disable()

                    stats = pstats.Stats(self.profiler)
                    stats.sort_stats('cumulative')

                    if output_file:
                        stats_path = Path(output_file)
                        stats_path.parent.mkdir(parents=True, exist_ok=True)
                        stats.dump_stats(str(stats_path))
                    else:
                        stats.print_stats()

                return result

            return wrapper

        return decorator


class ProfilerContext:
    """Context manager for profiling code blocks."""

    def __init__(self, name: str, print_results: bool = True):
        self.name = name
        self.print_results = print_results
        self.profiler = cProfile.Profile()
        self.logger = get_logger()

    def __enter__(self):
        self.profiler.enable()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.profiler.disable()
        if self.print_results:
            stats = pstats.Stats(self.profiler)
            stats.sort_stats('cumulative')
            self.logger.info(f"\nProfile results for '{self.name}':")
            stats.print_stats()


# Global profiler instance
_profiler = AddonProfiler()


def profile_function(output_file: Optional[Union[str, Path]] = None):
    """Convenience decorator for profiling functions."""
    return _profiler.profile_function(output_file)


def start_timer(name: str):
    """Start a named timer."""
    _profiler.start_timer(name)


def stop_timer(name: str) -> float:
    """Stop a named timer and return elapsed time."""
    return _profiler.stop_timer(name)


def profile_block(name: str, print_results: bool = True):
    """Context manager for profiling code blocks."""
    return ProfilerContext(name, print_results)
