from abc import ABC, abstractmethod


class IClimateChamber(ABC):
    """Interface defining the contract for any climate chamber implementation."""
    #TODO extend Interface implementation
    @abstractmethod
    def initialize_modules(self):
        pass
    @abstractmethod
    def set_heating(self, power: float):
        pass
    @abstractmethod
    def set_cooling(self, power: float):
        pass
    @abstractmethod
    def stop_all(self):
        pass
    @abstractmethod
    def cleanup(self):
        pass