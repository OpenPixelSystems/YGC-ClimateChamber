try:
    import RPi.GPIO as GPIO

    print("[GPIO_PROVIDER] [Import] Running with real RPi.GPIO")
except (ImportError, RuntimeError):
    print("[GPIO_PROVIDER] [Import] Running with mock GPIO")

    class MockPWM:
        def __init__(self, pin, frequency):
            self.pin = pin
            self.frequency = frequency
            print(
                f"[GPIO_PROVIDER] [MockPWM] PWM initialized on pin {pin} at {frequency}Hz"
            )

        def start(self, duty_cycle):
            print(
                f"[GPIO_PROVIDER] [MockPWM] PWM on pin {self.pin} started with duty cycle {duty_cycle}%"
            )

        def ChangeDutyCycle(self, duty_cycle):
            print(
                f"[GPIO_PROVIDER] [MockPWM] PWM on pin {self.pin} changed to duty cycle {duty_cycle}%"
            )

        def stop(self):
            print(f"[GPIO_PROVIDER] [MockPWM] PWM on pin {self.pin} stopped")

    class MockGPIO:
        BCM = "BCM"
        OUT = "OUT"
        IN = "IN"
        HIGH = 1
        LOW = 0

        def setmode(self, mode):
            print(f"[GPIO_PROVIDER] [MockGPIO] setmode({mode})")

        def setup(self, pin, mode):
            print(f"[GPIO_PROVIDER] [MockGPIO] setup(pin={pin}, mode={mode})")

        def output(self, pin, state):
            print(f"[GPIO_PROVIDER] [MockGPIO] output(pin={pin}, state={state})")

        def input(self, pin):
            print(f"[GPIO_PROVIDER] [MockGPIO] input(pin={pin}) -> LOW")
            return self.LOW

        def PWM(self, pin, frequency):
            print(f"[GPIO_PROVIDER] [MockGPIO] PWM(pin={pin}, frequency={frequency})")
            return MockPWM(pin, frequency)

        def cleanup(self):
            print("[GPIO_PROVIDER] [MockGPIO] cleanup()")

    GPIO = MockGPIO()

# Unified interface for importing
gpio = GPIO
