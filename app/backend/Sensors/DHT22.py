import os
import random
import sys
from typing import Dict, Optional
from app.backend.Providers.gpio_provider import gpio
from app.backend.Interfaces.ISensor import ISensor


class DHT22(ISensor):
    """Implementation of the DHT22 temperature and humidity sensor."""

    def __init__(self, name: str, pin: int, min_value: float, max_value: float, unit: str):
        """Initialize the DHT22 sensor.

        Args:
            name: Name of the sensor
            pin: GPIO pin number
            min_value: Minimum expected value
            max_value: Maximum expected value
            unit: Unit of measurement ('C' for temperature, '%' for humidity)
        """
        self._name = name
        self._pin = pin
        self._min_value = min_value
        self._max_value = max_value
        self._unit = unit
        self._is_temperature = unit == 'C'
        self._is_testing = self._detect_testing_environment()
        self._last_reading = None
        self.initialize()

    def _detect_testing_environment(self) -> bool:
        """Detect if we're in a testing environment based on GPIO provider.

        Returns:
            True if in testing environment, False if on real hardware
        """
        # Check if we're using the MockGPIO from gpio_provider
        from app.backend.Providers.gpio_provider import GPIO
        is_mock = hasattr(GPIO, '__name__') and GPIO.__name__ == 'MockGPIO'

        # Additional check for actual Raspberry Pi hardware
        is_not_pi = not (
                os.path.exists('/opt/vc/bin/') or
                os.path.exists('/sys/firmware/devicetree/base/model') or
                os.path.exists('/proc/device-tree/model')
        )

        return is_mock or is_not_pi

    def initialize(self) -> None:
        """Initialize the sensor hardware."""
        gpio.setmode(gpio.BCM)
        gpio.setup(self._pin, gpio.IN)
        print(f"[DHT22] Initialized sensor on pin {self._pin}, testing mode: {self._is_testing}")

    def _get_simulated_value(self) -> float:
        """Generate a simulated sensor value with natural variation starting from room temperature.

        Returns:
            Simulated sensor reading with realistic variation.
        """
        # Initialize with room temperature
        if self._last_reading is None:
            self._last_reading = 20.0

        # Apply small random variation
        variation = random.uniform(-0.3, 0.3)
        new_value = self._last_reading + variation

        # Keep value within specified min and max bounds
        new_value = max(self._min_value, min(self._max_value, new_value))
        self._last_reading = new_value

        return round(new_value, 1)

    def read(self) -> Dict[str, Optional[float]]:
        """Read temperature or humidity from the DHT22 sensor.

        Returns:
            Dictionary mapping sensor name to its reading value
        """
        json_format = {}

        try:
            if not self._is_testing:
                # We're on a real Raspberry Pi with actual GPIO, try to read the real sensor
                try:
                    import Adafruit_DHT
                    humidity, temperature = Adafruit_DHT.read_retry(Adafruit_DHT.DHT22, self._pin)

                    if humidity is not None and temperature is not None:
                        value = temperature if self._is_temperature else humidity
                        json_format[self._name] = value
                        self._last_reading = value  # Store for future reference
                        print(f"[DHT22] Read actual sensor value: {value} {self._unit}")
                    else:
                        # Sensor read failed, fallback to simulated value with a note
                        value = self._get_simulated_value()
                        json_format[self._name] = value
                        print(f"[DHT22] Sensor read failed, using simulated value: {value} {self._unit}")
                except ImportError:
                    # Adafruit library not available despite being on Pi, use simulated values
                    value = self._get_simulated_value()
                    json_format[self._name] = value
                    print(f"[DHT22] Adafruit library not available, using simulated value: {value} {self._unit}")
            else:
                # We're in a testing environment (using MockGPIO), use a simulated value
                value = self._get_simulated_value()
                json_format[self._name] = value
                print(f"[DHT22] In testing environment, using simulated value: {value} {self._unit}")

        except Exception as e:
            print(f"[DHT22] Error reading sensor {self._name}: {str(e)}")
            json_format[self._name] = None

        return json_format

    @property
    def name(self) -> str:
        return self._name

    @property
    def pin(self) -> int:
        return self._pin

    @property
    def min_value(self) -> float:
        return self._min_value

    @property
    def max_value(self) -> float:
        return self._max_value

    @property
    def unit(self) -> str:
        return self._unit

    @property
    def is_testing(self) -> bool:
        return self._is_testing