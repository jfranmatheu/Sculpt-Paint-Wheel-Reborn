from collections import defaultdict


class CallbackList:
    def __init__(self):
        self.callbacks = []

    def add_callback(self, callback):
        self.callbacks.append(callback)

    def remove_callback(self, callback):
        self.callbacks.remove(callback)

    def clear_callbacks(self):
        self.callbacks.clear()

    def call_callbacks(self, *args, **kwargs):
        for callback in self.callbacks:
            callback(*args, **kwargs)
    
    def __bool__(self):
        return len(self.callbacks) > 0
    
    def __iadd__(self, callback):
        """Allow subscribing callbacks with += operator."""
        self.add_callback(callback)
        return self
    
    def __isub__(self, callback):
        """Allow unsubscribing callbacks with -= operator."""
        self.remove_callback(callback)
        return self
    
    def __call__(self, *args, **kwargs):
        """Allow calling all callbacks by calling the callback list object."""
        self.call_callbacks(*args, **kwargs)


class CallbackDict:
    def __init__(self):
        self.callbacks = defaultdict(CallbackList)

    def add_callback(self, callback_id, callback):
        self.callbacks[callback_id].add_callback(callback)

    def remove_callback(self, callback_id, callback):
        self.callbacks[callback_id].remove_callback(callback)

    def clear_callbacks(self):
        self.callbacks.clear()

    def call_callbacks(self, callback_id, *args, default=None, **kwargs):
        if callback_list := self.callbacks.get(callback_id, None):
            callback_list.call_callbacks(*args, **kwargs)
        else:
            if default is not None:
                default(*args, **kwargs)

    def __bool__(self):
        return any(self.callbacks.values())

    def __contains__(self, callback_id):
        cl = self.callbacks.get(callback_id, None)
        return bool(cl) if cl is not None else False

    def __iadd__(self, callback_tuple):
        """Allow subscribing callbacks with += operator.
        
        Args:
            callback_tuple: Tuple of (callback_id, callback) to subscribe
        """
        callback_id, callback = callback_tuple
        self.add_callback(callback_id, callback)
        return self

    def __isub__(self, callback_tuple):
        """Allow unsubscribing callbacks with -= operator.
        
        Args:
            callback_tuple: Tuple of (callback_id, callback) to unsubscribe
        """
        callback_id, callback = callback_tuple
        self.remove_callback(callback_id, callback)
        return self

    def __call__(self, callback_id, *args, default=None, **kwargs):
        """Allow calling all callbacks for a specific ID by calling the callback dict object.
        
        Args:
            callback_id: ID of the callback to call
            default: Default value to return if no callbacks are found for the ID
        """
        self.call_callbacks(callback_id, *args, default=default, **kwargs)
