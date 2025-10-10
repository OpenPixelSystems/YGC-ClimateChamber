from abc import ABC, abstractmethod

from app.backend.Dataclasses.Config import PeltierConfig


class IPeltierModule(ABC):
    """Interface for sensor implementations."""

    @abstractmethod
    def __init__(self, peltier_config: PeltierConfig):
        """Initialize the peltier module."""
        pass

    def initialize(self) -> None:
        """Initialize the peltier hardware."""
        pass

    @abstractmethod
    def enable(self):
        pass

    @abstractmethod
    def disable(self):
        pass
