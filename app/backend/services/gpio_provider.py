try:
    import RPi.GPIO as GPIO
    print("Running with real RPi.GPIO")
except (ImportError, RuntimeError):
    print("Running with mock GPIO")

    class MockGPIO:
        BCM = 'BCM'
        OUT = 'OUT'
        IN = 'IN'
        HIGH = 1
        LOW = 0

        def setmode(self, mode):
            print(f"[MOCK] setmode({mode})")

        def setup(self, pin, mode):
            print(f"[MOCK] setup(pin={pin}, mode={mode})")

        def output(self, pin, state):
            print(f"[MOCK] output(pin={pin}, state={state})")

        def input(self, pin):
            print(f"[MOCK] input(pin={pin}) -> LOW")
            return self.LOW

        def cleanup(self):
            print("[MOCK] cleanup()")

    GPIO = MockGPIO()

# Expose GPIO as the thing that is either real or mock
gpio = GPIO