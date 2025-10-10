from abc import ABC, abstractmethod

from app.backend.Dataclasses.Config import FanConfig


class IFanModule(ABC):
    """Interface for sensor implementations."""

    @abstractmethod
    def __init__(self, fan_config: FanConfig):
        """Initialize the peltier module."""
        pass

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the peltier hardware."""
        pass

    @abstractmethod
    def activate(self) -> None:
        pass

    @abstractmethod
    def deactivate(self) -> None:
        pass
