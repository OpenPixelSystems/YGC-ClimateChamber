from abc import ABC, abstractmethod


class ISensorModule(ABC):
    """Interface defining the contract for any sensor module implementation."""

    @abstractmethod
    def get_sensors(self):
        """Get sensor data from sensorModule"""
        pass