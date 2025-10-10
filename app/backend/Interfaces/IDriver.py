from abc import ABC, abstractmethod

from app.backend.Dataclasses.Config import DriverConfig


class IDriver(ABC):
    """Interface for sensor implementations."""

    @abstractmethod
    def __init__(self, config: DriverConfig):
        pass

    @abstractmethod
    def heat(self, duty_cycle=20):
        pass

    @abstractmethod
    def cool(self, duty_cycle=20):
        pass

    @abstractmethod
    def stop(self):
        pass

    @abstractmethod
    def cleanup(self):
        pass
