class MockGPIO:
    """mock GPIO class to simulate Raspberry Pi GPIO behavior."""

    BCM = "BCM"
    OUT = "OUT"

    @staticmethod
    def setmode(mode):
        print(f"MockGPIO: Mode set to {mode}")

    @staticmethod
    def setup(pin, mode):
        print(f"MockGPIO: Pin {pin} set to mode {mode}")

    @staticmethod
    def cleanup():
        print("MockGPIO: Cleanup called")