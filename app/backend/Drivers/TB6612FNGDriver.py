from app.backend.Dataclasses.Config import PeltierConfig
from app.backend.Interfaces.IDriver import IDriver
from app.backend.Providers.gpio_provider import GPIO


class TB6612FNGDriver(IDriver):

    def __init__(self, config: PeltierConfig):
        self.config = config
        self.pwm = None

        # Initialize GPIO mode
        GPIO.setmode(GPIO.BCM)

        # Setup GPIO pins
        self._setup_pins()
        print(
            f"[TB6612FNGDriver] [Init] initialised TB6612FNG driver module using {config}"
        )

    def _setup_pins(self):
        """Initialize GPIO pins for TB6612FNG"""
        # Setup pins
        GPIO.setup(self.config.LPWM, GPIO.OUT)  # GPIO22 -> AIN2 (heating enable)
        GPIO.setup(self.config.R_EN, GPIO.OUT)  # GPIO27 -> AIN1 (cooling enable)
        GPIO.setup(self.config.RPWM, GPIO.OUT)  # GPIO18 -> PWMA (PWM speed)

        # Initialize all pins to LOW (stopped state)
        GPIO.output(self.config.LPWM, GPIO.LOW)  # AIN2 = LOW
        GPIO.output(self.config.R_EN, GPIO.LOW)  # AIN1 = LOW

        # Initialize PWM on PWMA pin
        self.pwm = GPIO.PWM(self.config.RPWM, self.config.PWM_FREQUENCY)
        self.pwm.start(0)  # Start with 0% duty cycle

    def heat(self, scaled_duty: int = 20):

        print(
            f"TB6612FNG: HEATING - AIN2=HIGH (GPIO{self.config.LPWM}), "
            f"AIN1=LOW (GPIO{self.config.R_EN}), PWM={scaled_duty}%"
        )

        # Set heating direction: AIN1=LOW, AIN2=HIGH
        GPIO.output(self.config.R_EN, GPIO.LOW)  # AIN1 = LOW (cooling OFF)
        GPIO.output(self.config.LPWM, GPIO.HIGH)  # AIN2 = HIGH (heating ON)

        # Set PWM duty cycle on PWMA
        self.pwm.ChangeDutyCycle(scaled_duty)

    def cool(self, scaled_duty: int = 20):

        print(
            f"TB6612FNG: COOLING - AIN1=HIGH (GPIO{self.config.R_EN}), "
            f"AIN2=LOW (GPIO{self.config.LPWM}), PWM={scaled_duty}%"
        )

        # Set cooling direction: AIN1=HIGH, AIN2=LOW
        GPIO.output(self.config.R_EN, GPIO.HIGH)  # AIN1 = HIGH (cooling ON)
        GPIO.output(self.config.LPWM, GPIO.LOW)  # AIN2 = LOW (heating OFF)

        # Set PWM duty cycle on PWMA
        self.pwm.ChangeDutyCycle(scaled_duty)

    def stop(self):
        """Stop motor: AIN1=LOW, AIN2=LOW, PWMA=0"""
        print("TB6612FNG: STOP - All pins LOW")

        # Stop PWM first
        self.pwm.ChangeDutyCycle(0)

        # Set both direction pins LOW (brake/stop)
        GPIO.output(self.config.R_EN, GPIO.LOW)  # AIN1 = LOW
        GPIO.output(self.config.LPWM, GPIO.LOW)  # AIN2 = LOW

    def cleanup(self):
        """Clean up GPIO resources"""
        self.stop()

        if self.pwm:
            self.pwm.stop()

        GPIO.cleanup()
