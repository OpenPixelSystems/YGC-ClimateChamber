from app.backend.Dataclasses.Config import FanConfig
from app.backend.Interfaces.IFanModule import IFanModule
from app.backend.Providers.gpio_provider import GPIO


class FanModule(IFanModule):
    def __init__(self, config: FanConfig):
        self.name = FanConfig.name
        self.type = FanConfig.type
        self.EN = config.EN
        self.initialize()

    def initialize(self) -> None:
        print(f"[FanModule] [Initialize] Fan module initialized on pin {self.EN}.")
        GPIO.setup(self.EN, GPIO.OUT)
        GPIO.output(self.EN, GPIO.LOW)

    def activate(self) -> None:
        GPIO.output(self.EN, GPIO.HIGH)

    def deactivate(self):
        GPIO.output(self.EN, GPIO.LOW)