from gpu import state as gpu_state


class CM_GPU_BLEND:
    """Context manager for GPU blend state.
        Solves if inside of a nested context manager.
    """
    _current_depth: int = 0

    def __init__(self, blend: str = 'ALPHA'):
        self.blend = blend
        self.last_blend = gpu_state.blend_get()
        CM_GPU_BLEND._current_depth += 1
        if CM_GPU_BLEND._current_depth > 1 and self.blend != self.last_blend:
            self.blend = None
    def __enter__(self):
        if self.blend is not None:
            gpu_state.blend_set(self.blend)
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.blend is not None:
            gpu_state.blend_set(self.last_blend)
        CM_GPU_BLEND._current_depth -= 1


def gpu_state_blend(blend: str = 'ALPHA'):
    """Decorator to set the GPU blend state.

    Args:
        blend (str, optional): The blend mode to set. Defaults to 'ALPHA'.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            with CM_GPU_BLEND(blend):
                return func(*args, **kwargs)
        return wrapper
    return decorator
