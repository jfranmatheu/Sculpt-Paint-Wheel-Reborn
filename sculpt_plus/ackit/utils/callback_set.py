from collections import defaultdict


class CallbackSet:
    def __init__(self):
        self.callbacks = defaultdict(list)

    def add_callback(self, callback_id, callback):
        self.callbacks[callback_id].append(callback)

    def remove_callback(self, callback_id, callback):
        self.callbacks[callback_id].remove(callback)

    def clear_callbacks(self):
        self.callbacks.clear()

    def call_callbacks(self, callback_id):
        for callback in self.callbacks[callback_id]:
            callback()
