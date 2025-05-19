from abc import ABC, abstractmethod


class ISubscriptable(ABC):
    def subscribe(self, callback):
        pass

    def unsubscribe(self, callback):
        pass

    def notify(self, data):
        pass