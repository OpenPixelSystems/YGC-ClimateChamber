from abc import ABC, abstractmethod


class IFanModule(ABC):
    """Interface defining the contract for any Fan module implementation."""

    @abstractmethod
    def set_power(self, power):
        pass