from app.backend.Dataclasses.Config import PeltierConfig
from app.backend.Drivers.BTS7960Driver import BTS7960Driver
from app.backend.Drivers.TB6612FNGDriver import TB6612FNGDriver
from app.backend.Interfaces.IPeltierModule import IPeltierModule
from app.backend.Providers.gpio_provider import GPIO
from enum import Enum


class DriverType(Enum):
    TB6612FNG = "TB6612FNG"
    BTS7960 = "BTS7960"


class PeltierModule(IPeltierModule):
    def __init__(self, config: PeltierConfig):
        self.config = config
        self.driver_type = config.driver_type

        GPIO.setmode(GPIO.BCM)

        self.max_duty_cycle: int = config.Duty_cycle_limit or 50

        if self.driver_type == DriverType.TB6612FNG.value:
            self.driver = TB6612FNGDriver(config)
        elif self.driver_type == DriverType.BTS7960.value:
            self.driver = BTS7960Driver(config)
        else:
            raise ValueError(f"Unsupported driver type: {self.driver_type}")

    def _rescale_duty(self, duty_cycle: int) -> float:
        """Rescale 0–100% input to 0–max_duty_cycle%"""
        duty_cycle = max(0, min(100, duty_cycle))  # Clamp input to 0–100
        return (duty_cycle / 100) * self.max_duty_cycle

    def heat(self, duty_cycle=100):
        """Enable heating: AIN1=LOW, AIN2=HIGH, PWMA=PWM"""
        scaled_duty = self._rescale_duty(duty_cycle)
        self.driver.heat(scaled_duty)
        return scaled_duty

    def cool(self, duty_cycle=100):
        """Enable cooling: AIN1=HIGH, AIN2=LOW, PWMA=PWM"""
        scaled_duty = self._rescale_duty(duty_cycle)
        self.driver.cool(scaled_duty)
        return scaled_duty

    def stop(self):
        """Stop motor: AIN1=LOW, AIN2=LOW, PWMA=0"""
        self.driver.stop()

    def cleanup(self):
        """Clean up GPIO resources"""
        self.driver.cleanup()

    def enable(self):
        self.driver.enable()

    def disable(self):
        self.driver.disable()
