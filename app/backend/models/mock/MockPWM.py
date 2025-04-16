class MockPWM:
    """mock PWM class to simulate PWM behavior."""

    def __init__(self, pin, frequency):
        self.pin = pin
        self.frequency = frequency
        print(f"MockPWM initialized on pin {pin} with frequency {frequency}Hz")

    def start(self, duty_cycle):
        print(f"MockPWM on pin {self.pin}: Started with duty cycle {duty_cycle}%")

    def ChangeDutyCycle(self, duty_cycle):
        print(f"MockPWM on pin {self.pin}: Duty cycle changed to {duty_cycle}%")

    def stop(self):
        print(f"MockPWM on pin {self.pin}: Stopped")
