from abc import ABC, abstractmethod


class IClimateChamber(ABC):
    """Interface defining the contract for any climate chamber implementation."""
    @abstractmethod
    def initialize_modules(self):
        pass

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def stop(self):
        pass

    @abstractmethod
    def enable_peltier_modules(self):
        pass

    @abstractmethod
    def disable_peltier_modules(self):
        pass

