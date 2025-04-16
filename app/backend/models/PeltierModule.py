import asyncio
from abc import ABC
from time import sleep

from app.backend.models.interfaces.IPeltierModule import *

class PeltierModule(IPeltierModule):
    _instance = None  # Singleton instance

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(PeltierModule, cls).__new__(cls)
        return cls._instance

    def __init__(self, name, heating_pin, cooling_pin):
        self.name = name
        self.heating_pin = heating_pin
        self.cooling_pin = cooling_pin
        asyncio.create_task(self.start())

    def _initialize_pwm(self):
        # Real GPIO initialization code here
        pass

    @abstractmethod
    async def start(self):
        while True:
            print("Peltier Module instance created, infinite steering loop enabled")
            sleep(5)

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
