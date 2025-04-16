from app.backend.models.interfaces.IClimateChamber import *
from app.backend.models.mock.MockGPIO import MockGPIO
from app.backend.models.mock.MockPWM import MockPWM

class MockClimateChamber(IClimateChamber):
    _instance = None

    HEAT_PIN = 18
    COOL_PIN = 23
    PWM_FREQUENCY = 1000

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(MockClimateChamber, cls).__new__(cls)
            cls._instance._initialize_pwm()
        return cls._instance

    def _initialize_pwm(self):
        print("\nInitializing ClimateChamber with MockPWM and MockGPIO...")
        MockGPIO.setmode(MockGPIO.BCM)
        MockGPIO.setup(self.HEAT_PIN, MockGPIO.OUT)
        MockGPIO.setup(self.COOL_PIN, MockGPIO.OUT)

        self.heat_pwm = MockPWM(self.HEAT_PIN, self.PWM_FREQUENCY)
        self.cool_pwm = MockPWM(self.COOL_PIN, self.PWM_FREQUENCY)

        self.heat_pwm.start(0)
        self.cool_pwm.start(0)

    def set_heating(self, power: float):
        power = max(0, min(100, power))
        print(f"\nMockClimateChamber: Setting heating power to {power}%")

    def set_cooling(self, power: float):
        power = max(0, min(100, power))
        print(f"\nMockClimateChamber: Setting cooling power to {power}%")

    def stop_all(self):
        print("\nMockClimateChamber: Stopping all processes")

    def cleanup(self):
        print("\nMockClimateChamber: Cleaning up resources")
