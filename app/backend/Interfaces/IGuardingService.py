from abc import ABC, abstractmethod
from typing import Dict, Callable

class IGuardingService(ABC):
    @abstractmethod
    def monitor_temperature(self, temperature_data):
        pass

    @abstractmethod
    def monitor_current(self, current_data):
        pass