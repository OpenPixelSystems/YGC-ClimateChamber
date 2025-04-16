from app.backend.models.interfaces.IFanModule import *

class FanModule(IFanModule):
    _instance = None  # Singleton instance

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(FanModule, cls).__new__(cls)
        return cls._instance

    def __init__(self, power_pin, name="fan"):
        self.name = name
        self.heating_pin = power_pin

    def _initialize_pwm(self):
        # Real GPIO initialization code here
        pass

    @abstractmethod
    def set_heating(self, power: float):
        power = max(0, min(100, power))
        # Real implementation

    @abstractmethod
    def set_cooling(self, power: float):
        power = max(0, min(100, power))
        # Real implementation

    @abstractmethod
    def stop_all(self):
        return
