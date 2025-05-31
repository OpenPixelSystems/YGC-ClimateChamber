from app.backend.Dataclasses.Config import PeltierConfig
from app.backend.Interfaces.IPeltierModule import IPeltierModule
from app.backend.Providers.gpio_provider import GPIO


class PeltierModule(IPeltierModule):
    def __init__(self, config: PeltierConfig):
        self.config = config

        GPIO.setmode(GPIO.BCM)

        # Setup BTS7960 pins
        GPIO.setup(config.RPWM, GPIO.OUT)
        GPIO.setup(config.LPWM, GPIO.OUT)
        GPIO.setup(config.R_EN, GPIO.OUT)
        GPIO.setup(config.L_EN, GPIO.OUT)

        # Enable both sides by default
        GPIO.output(config.R_EN, GPIO.HIGH)
        GPIO.output(config.L_EN, GPIO.HIGH)

        # Initialize PWM on both pins
        self.r_pwm = GPIO.PWM(config.RPWM, config.PWM_FREQUENCY)
        self.l_pwm = GPIO.PWM(config.LPWM, config.PWM_FREQUENCY)

        self.max_duty_cycle : int = config.Duty_cycle_limit or 50

        self.r_pwm.start(0)
        self.l_pwm.start(0)

    def _rescale_duty(self, duty_cycle: int) -> float:
        """Rescale 0–100% input to 0–max_duty_cycle%"""
        duty_cycle = max(0, min(100, duty_cycle))  # Clamp input to 0–100
        return (duty_cycle / 100) * self.max_duty_cycle

    def heat(self, duty_cycle=100):
        """Drive current in one direction (e.g., heating)"""
        scaled_duty = self._rescale_duty(duty_cycle)
        self.l_pwm.ChangeDutyCycle(0)
        self.r_pwm.ChangeDutyCycle(scaled_duty)
        return scaled_duty

    def cool(self, duty_cycle=100):
        """Drive current in the other direction (e.g., cooling)"""
        scaled_duty = self._rescale_duty(duty_cycle)
        self.r_pwm.ChangeDutyCycle(0)
        self.l_pwm.ChangeDutyCycle(scaled_duty)
        return scaled_duty

    def stop(self):
        """Stop all PWM signals"""
        self.r_pwm.ChangeDutyCycle(0)
        self.l_pwm.ChangeDutyCycle(0)

    def cleanup(self):
        self.stop()
        self.r_pwm.stop()
        self.l_pwm.stop()
        GPIO.cleanup()
