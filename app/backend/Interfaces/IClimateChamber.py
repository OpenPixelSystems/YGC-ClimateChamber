from abc import ABC, abstractmethod


class IClimateChamber(ABC):
    """Interface defining the contract for any climate chamber implementation."""
    @abstractmethod
    def initialize_modules(self):
        pass
