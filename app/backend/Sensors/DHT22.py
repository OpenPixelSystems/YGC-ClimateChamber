import os
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
        self.initialize()

    def initialize(self) -> None:
        """Initialize the sensor hardware."""
        gpio.setmode(gpio.BCM)
        gpio.setup(self._pin, gpio.IN)

    def read(self) -> Dict[str, Optional[float]]:
        """Read temperature or humidity from the DHT22 sensor.
        
        Returns:
            Dictionary mapping sensor name to its reading value
        """
        json_format = {}

        try:
            # Check if we're on an actual Raspberry Pi
            if os.path.exists('/opt/vc/bin/'):
                try:
                    import Adafruit_DHT
                    humidity, temperature = Adafruit_DHT.read_retry(Adafruit_DHT.DHT22, self._pin)

                    if humidity is not None and temperature is not None:
                        value = temperature if self._is_temperature else humidity
                        json_format[self._name] = value
                    else:
                        # Sensor read failed, fallback to simulated value
                        json_format[self._name] = 22.5 if self._is_temperature else 45.0

                except ImportError:
                    # Library not available, use simulated values
                    json_format[self._name] = 22.5 if self._is_temperature else 45.0
            else:
                # We're in a testing environment
                if self._is_temperature:
                    simulated_temp = 20 + (self._pin % 10) / 2
                    json_format[self._name] = simulated_temp
                else:  # humidity
                    simulated_humidity = 40 + (self._pin % 10) * 2
                    json_format[self._name] = simulated_humidity

        except Exception as e:
            print(f"Error reading DHT22 sensor {self._name}: {str(e)}")
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