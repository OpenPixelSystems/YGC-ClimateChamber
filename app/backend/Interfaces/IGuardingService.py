from abc import ABC, abstractmethod


class IGuardingService(ABC):
    @abstractmethod
    def monitor_temperature(self, temperature_data):
        pass

    @abstractmethod
    def monitor_current(self, current_data):
        pass

    @abstractmethod
    def get_guarding_state(self):
        pass

    @abstractmethod
    def get_guarding_info(self):
        pass
