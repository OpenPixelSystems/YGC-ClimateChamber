from abc import ABC, abstractmethod
from typing import Dict, Optional


class ISensor(ABC):
    """Interface for sensor implementations."""

    @abstractmethod
    def __init__(self, name: str, pin: int, min_value: float, max_value: float, unit: str):
        """Initialize the sensor.
        
        Args:
            name: Name of the sensor
            pin: GPIO pin number
            min_value: Minimum expected value
            max_value: Maximum expected value
            unit: Unit of measurement
        """
        pass

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the sensor hardware."""
        pass

    @abstractmethod
    def read(self) -> Dict[str, Optional[float]]:
        """Read the sensor value.
        
        Returns:
            Dictionary mapping sensor name to its reading value
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Get the sensor name."""
        pass

    @property
    @abstractmethod
    def pin(self) -> int:
        """Get the GPIO pin number."""
        pass

    @property
    @abstractmethod
    def min_value(self) -> float:
        """Get the minimum expected value."""
        pass

    @property
    @abstractmethod
    def max_value(self) -> float:
        """Get the maximum expected value."""
        pass

    @property
    @abstractmethod
    def unit(self) -> str:
        """Get the unit of measurement."""
        pass