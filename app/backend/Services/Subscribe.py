from app.backend.Interfaces.ISubscribe import ISubscriptable


class Subscriptable(ISubscriptable):
    def __init__(self):
        self.listeners = []

    def subscribe(self, callback):
        self.listeners.append(callback)

    def unsubscribe(self, callback):
        if callback in self.listeners:
            self.listeners.remove(callback)

    def notify(self, data):
        for callback in self.listeners:
            callback(data)
