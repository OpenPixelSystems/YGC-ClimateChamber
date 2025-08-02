from abc import ABC, abstractmethod
from typing import Dict, Callable

class ISensorReader(ABC):
    """Interface for sensor reading functionality."""

    @abstractmethod
    def read_sensors(self) -> Dict[str,Dict[str, float]]:
        """Read all connected Sensors.
        
        Returns:
            Dictionary mapping sensor names to their readings
        """
        pass

    @abstractmethod
    def subscribe(self,callback):
        pass
    
    @abstractmethod
    def set_peltier_enabled(self, enabled: bool):
        """Set whether peltier modules are enabled.
        
        Args:
            enabled: True if peltier modules are enabled, False otherwise
        """
        pass