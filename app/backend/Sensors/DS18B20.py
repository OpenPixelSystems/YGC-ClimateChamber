import os
from typing import Dict, Optional
from app.backend.Providers.gpio_provider import gpio
from app.backend.Interfaces.ISensor import ISensor


class DS18B20(ISensor):
    """Implementation of the DS18B20 temperature sensor."""

    def __init__(self, name: str, pin: int, min_value: float, max_value: float, unit: str):
        """Initialize the DS18B20 sensor.
        
        Args:
            name: Name of the sensor
            pin: GPIO pin number
            min_value: Minimum expected value
            max_value: Maximum expected value
            unit: Unit of measurement (should be 'C' for temperature)
        """
        self._name = name
        self._pin = pin
        self._min_value = min_value
        self._max_value = max_value
        self._unit = unit
        self.initialize()

    def initialize(self) -> None:
        """Initialize the sensor hardware."""
        gpio.setmode(gpio.BCM)
        gpio.setup(self._pin, gpio.IN)

    def read(self) -> Dict[str, Optional[float]]:
        """Read temperature from the DS18B20 sensor.
        
        Returns:
            Dictionary mapping sensor name to its reading value
        """
        json_format = {}

        try:
            # On a real Raspberry Pi with real Sensors, the 1-Wire interface is used
            if os.path.exists('/sys/bus/w1/devices/'):
                # Find sensor by its ID - in a real implementation you'd map GPIO pins to sensor IDs
                sensor_dirs = os.listdir('/sys/bus/w1/devices/')
                sensor_folder = next((folder for folder in sensor_dirs if folder.startswith('28-')), None)

                if sensor_folder:
                    sensor_path = f'/sys/bus/w1/devices/{sensor_folder}/w1_slave'

                    with open(sensor_path, 'r') as f:
                        lines = f.readlines()

                    # Check if the CRC check passed (the 'YES' at the end of the first line)
                    if lines[0].strip().endswith('YES'):
                        # Find the temperature value (t=<value> in the second line)
                        temp_pos = lines[1].find('t=')
                        if temp_pos != -1:
                            # Convert the value (1/1000 degrees C)
                            temp_string = lines[1][temp_pos + 2:]
                            temp_c = float(temp_string) / 1000.0
                            json_format[self._name] = temp_c
                        else:
                            json_format[self._name] = None  # Could not find temperature data
                    else:
                        json_format[self._name] = None  # CRC check failed
                else:
                    # No sensor found, so simulate in test environment
                    json_format[self._name] = 22.5  # Default test temperature
            else:
                # We're in a test environment
                # Simulate a temperature reading based on pin
                simulated_temp = 20 + (self._pin % 10) / 2
                json_format[self._name] = simulated_temp

        except Exception as e:
            print(f"Error reading DS18B20 sensor {self._name}: {str(e)}")
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
