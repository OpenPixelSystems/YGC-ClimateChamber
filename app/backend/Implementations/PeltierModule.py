from app.backend.Dataclasses.Config import PeltierConfig
from app.backend.Interfaces.IPeltierModule import IPeltierModule
from app.backend.Providers.gpio_provider import GPIO


class PeltierModule(IPeltierModule):
    #TODO Create logic able to control fan speed/direction based on temperature
    def __init__(self, config: PeltierConfig):
        self.config = config

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(config.gpio_pin_heating, GPIO.OUT)
        GPIO.setup(config.gpio_pin_cooling, GPIO.OUT)
        GPIO.setup(config.gpio_pin_pwm, GPIO.OUT)

        self.pwm = GPIO.PWM(config.gpio_pin_pwm, config.pwm_frequency)
        self.pwm.start(0)

    def heat(self, duty_cycle=100):
        GPIO.output(self.config.gpio_pin_cooling, GPIO.LOW)
        GPIO.output(self.config.gpio_pin_heating, GPIO.HIGH)
        self.pwm.ChangeDutyCycle(duty_cycle)

    def cool(self, duty_cycle=100):
        GPIO.output(self.config.gpio_pin_heating, GPIO.LOW)
        GPIO.output(self.config.gpio_pin_cooling, GPIO.HIGH)
        self.pwm.ChangeDutyCycle(duty_cycle)

    def stop(self):
        GPIO.output(self.config.gpio_pin_heating, GPIO.LOW)
        GPIO.output(self.config.gpio_pin_cooling, GPIO.LOW)
        self.pwm.ChangeDutyCycle(0)

    def cleanup(self):
        self.pwm.stop()
        GPIO.cleanup()
