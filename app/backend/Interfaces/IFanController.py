from abc import ABC, abstractmethod


class IFanController(ABC):

    @abstractmethod
    def __init__(self):
        """Initialize the Fan controller."""
        pass

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the fan modules from config."""
        pass

    @abstractmethod
    def activate(self) -> None:
        pass

    @abstractmethod
    def deactivate(self) -> None:
        pass
