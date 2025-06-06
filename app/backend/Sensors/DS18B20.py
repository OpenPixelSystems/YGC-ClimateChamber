import os
import random
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
        self._type = 'DS18B20'
        self._name = name
        self._pin = pin
        self._min_value = min_value
        self._max_value = max_value
        self._unit = unit
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
                os.path.exists('/proc/device-tree/model') or
                os.path.exists('/sys/bus/w1/devices/')  # 1-Wire interface exists
        )

        return is_mock or is_not_pi

    def initialize(self) -> None:
        """Initialize the sensor hardware."""
        gpio.setmode(gpio.BCM)
        gpio.setup(self._pin, gpio.IN)
        print(f"[DS18B20] Initialized sensor on pin {self._pin}, testing mode: {self._is_testing}")

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
        new_value = max(self._min_value, min(self._max_value+1, new_value))
        self._last_reading = new_value

        return round(new_value, 1)

    def read(self) -> Dict[str, Optional[float]]:
        """Read temperature from the DS18B20 sensor.

        Returns:
            Dictionary mapping sensor name to its reading value
        """
        json_format = {}

        try:
            if not self._is_testing and os.path.exists('/sys/bus/w1/devices/'):
                # On a real Raspberry Pi with 1-Wire interface
                try:
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
                                json_format[self._type] = {self._name: temp_c}
                                self._last_reading = temp_c  # Store for future reference
                                print(f"[DS18B20] Read actual sensor value: {temp_c} {self._unit}")
                            else:
                                # Could not find temperature data, return None instead of simulated value
                                json_format[self._type] = {self._name: None}
                                print(f"[DS18B20] Could not find temperature data, returning None")
                        else:
                            # CRC check failed, return None instead of simulated value
                            json_format[self._type] = {self._name: None}
                            print(f"[DS18B20] CRC check failed, returning None")
                    else:
                        # No sensor found, return None instead of simulated value
                        json_format[self._type] = {self._name: None}
                        print(f"[DS18B20] No sensor found, returning None")
                except Exception as e:
                    # Error reading sensor, return None instead of simulated value
                    json_format[self._type] = {self._name: None}
                    print(f"[DS18B20] Error reading real sensor: {str(e)}, returning None")
            else:
                # We're in a test environment or sensor initialization failed
                # Only use simulated values in testing environment
                if self._is_testing:
                    value = self._get_simulated_value()
                    json_format[self._type] = {self._name: value}
                    print(f"[DS18B20] In testing environment, using simulated value: {value} {self._unit}")
                else:
                    # On real hardware but 1-Wire interface not available
                    json_format[self._type] = {self._name: None}
                    print(f"[DS18B20] 1-Wire interface not available on real hardware, returning None")

        except Exception as e:
            print(f"[DS18B20] Critical error reading sensor {self._name}: {str(e)}")
            json_format[self._type] = {self._name: None}

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