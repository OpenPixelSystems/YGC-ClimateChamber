from app.backend.models.SensorModule import SensorModule
from app.backend.models.PeltierModule import PeltierModule
from app.backend.models.FanModule import FanModule
from app.backend.models.interfaces.IClimateChamber import *


# Real implementation
class ClimateChamber(IClimateChamber):
    _instance = None  # Singleton instance

    # Define GPIO pins for heating and cooling
    HEAT_PIN = 18
    COOL_PIN = 23
    PWM_FREQUENCY = 1000

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(ClimateChamber, cls).__new__(cls)
        return cls._instance

    def __init__(self, sensorModule=None, peltierModule=None, fanModule=None):
        self.sensorModule = SensorModule()
        self.peltierModule = PeltierModule("Single", 12, 13)
        self.fanModule = FanModule(10)

    def cleanup(self):
        return


