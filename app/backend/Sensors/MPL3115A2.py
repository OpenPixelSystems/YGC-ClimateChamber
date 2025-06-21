import os
import random
from typing import Dict, Optional
from app.backend.Interfaces.ISensor import ISensor


class MPL3115A2(ISensor):
    """Implementation of the MPL3115A2 pressure, altitude, and temperature sensor."""

    def __init__(self, name: str, sda_pin: int, scl_pin: int, min_value: float, max_value: float, unit: str):
        """Initialize the MPL3115A2 sensor.

        Args:
            name: Name of the sensor
            sda_pin: GPIO pin number for SDA (I2C data line)
            scl_pin: GPIO pin number for SCL (I2C clock line)
            min_value: Minimum expected value
            max_value: Maximum expected value
            unit: Unit of measurement ('hPa' for pressure, 'm' for altitude, 'C' for temperature)
        """
        self._type = 'MPL3115A2'
        self._name = name
        self._sda_pin = sda_pin
        self._scl_pin = scl_pin
        self._min_value = min_value
        self._max_value = max_value
        self._unit = unit
        self._is_testing = self._detect_testing_environment()
        self._last_readings = {
            'pressure': 1013.25,  # Standard atmospheric pressure in hPa
            'altitude': 0.0,  # Sea level
            'temperature': 20.0  # Room temperature
        }
        self._sensor = None
        self.initialize()

    def _detect_testing_environment(self) -> bool:
        """Detect if we're in a testing environment based on GPIO provider and hardware availability.

        Returns:
            True if in testing environment, False if on real hardware
        """
        # Check if we're using the MockGPIO from gpio_provider
        from app.backend.Providers.gpio_provider import GPIO
        is_mock = hasattr(GPIO, '__name__') and GPIO.__name__ == 'MockGPIO'

        # Additional check for actual Raspberry Pi hardware and I2C availability
        is_not_pi = not (
                os.path.exists('/opt/vc/bin/') or
                os.path.exists('/sys/firmware/devicetree/base/model') or
                os.path.exists('/proc/device-tree/model') or
                os.path.exists('/dev/i2c-1')  # I2C interface exists
        )

        # Check if required libraries are available
        try:
            import board
            import busio
            import adafruit_mpl3115a2
            libs_available = True
        except ImportError:
            libs_available = False

        return is_mock or is_not_pi or not libs_available

    def initialize(self) -> None:
        """Initialize the sensor hardware."""
        if not self._is_testing:
            try:
                import board
                import busio
                import adafruit_mpl3115a2

                # Set up I2C with specific pins
                i2c = busio.I2C(scl=getattr(board, f'D{self._scl_pin}', board.SCL),
                                sda=getattr(board, f'D{self._sda_pin}', board.SDA))
                self._sensor = adafruit_mpl3115a2.MPL3115A2(i2c)

                # Switch to Altimeter mode and set sea-level pressure
                self._sensor.sealevel_pressure = 1013.25  # Adjust based on local sea-level pressure

                print(
                    f"[MPL3115A2] Initialized real sensor on I2C (SDA: {self._sda_pin}, SCL: {self._scl_pin}), testing mode: {self._is_testing}")
            except Exception as e:
                print(f"[MPL3115A2] Failed to initialize real sensor: {str(e)}, switching to testing mode")
                self._is_testing = True
                self._sensor = None
        else:
            print(f"[MPL3115A2] Initialized in testing mode: {self._is_testing}")

    def _get_simulated_values(self) -> Dict[str, float]:
        """Generate simulated sensor values with natural variation.

        Returns:
            Dictionary with simulated pressure, altitude, and temperature readings.
        """
        # Apply small random variations to each measurement
        pressure_variation = random.uniform(-2.0, 2.0)  # ±2 hPa variation
        altitude_variation = random.uniform(-0.5, 0.5)  # ±0.5 m variation
        temp_variation = random.uniform(-0.2, 0.2)  # ±0.2°C variation

        # Update readings with variation
        new_pressure = self._last_readings['pressure'] + pressure_variation
        new_altitude = self._last_readings['altitude'] + altitude_variation
        new_temperature = self._last_readings['temperature'] + temp_variation

        # Keep values within reasonable bounds
        new_pressure = max(800.0, min(1200.0, new_pressure))  # Reasonable pressure range
        new_altitude = max(-500.0, min(5000.0, new_altitude))  # Reasonable altitude range
        new_temperature = max(-40.0, min(85.0, new_temperature))  # Sensor operating range

        # Store for next iteration
        self._last_readings['pressure'] = new_pressure
        self._last_readings['altitude'] = new_altitude
        self._last_readings['temperature'] = new_temperature

        return {
            'pressure': round(new_pressure, 2),
            'altitude': round(new_altitude, 2),
            'temperature': round(new_temperature, 2)
        }

    def read(self) -> Dict[str, Optional[float]]:
        """Read pressure, altitude, and temperature from the MPL3115A2 sensor.

        Returns:
            Dictionary mapping sensor type to sensor name and its reading value
        """
        json_format = {}

        try:
            if not self._is_testing and self._sensor is not None:
                # Read from real sensor
                try:
                    pressure = self._sensor.pressure
                    altitude = self._sensor.altitude
                    temperature = self._sensor.temperature

                    # Update last readings for future reference
                    self._last_readings['pressure'] = pressure
                    self._last_readings['altitude'] = altitude
                    self._last_readings['temperature'] = temperature

                    # Return the requested measurement based on unit
                    if self._unit.lower() == 'hpa':
                        value = pressure
                        measurement_type = 'pressure'
                    elif self._unit.lower() == 'm':
                        value = altitude
                        measurement_type = 'altitude'
                    elif self._unit.lower() == 'degrees':
                        value = temperature
                        measurement_type = 'temperature'
                    else:
                        # Default to pressure if unit is unclear
                        value = pressure
                        measurement_type = 'pressure'

                    json_format[self._type] = {self._name: round(value, 2)}
                    print(f"[MPL3115A2] Read actual sensor {measurement_type}: {value:.2f} {self._unit}")

                except Exception as e:
                    # Error reading sensor, return None instead of simulated values
                    json_format[self._type] = {self._name: None}
                    print(f"[MPL3115A2] Error reading real sensor: {str(e)}, returning None")
            else:
                # We're in a test environment or sensor initialization failed
                # Only use simulated values in testing environment
                if self._is_testing:
                    simulated_values = self._get_simulated_values()

                    if self._unit.lower() == 'hpa':
                        value = simulated_values['pressure']
                    elif self._unit.lower() == 'm':
                        value = simulated_values['altitude']
                    elif self._unit.lower() == 'degrees':
                        value = simulated_values['temperature']
                    else:
                        value = simulated_values['pressure']

                    json_format[self._type] = {self._name: value}
                    print(f"[MPL3115A2] In testing environment, using simulated value: {value} {self._unit}")
                else:
                    # On real hardware but sensor failed to initialize
                    json_format[self._type] = {self._name: None}
                    print(f"[MPL3115A2] Sensor initialization failed on real hardware, returning None")

        except Exception as e:
            print(f"[MPL3115A2] Critical error reading sensor {self._name}: {str(e)}")
            json_format[self._type] = {self._name: None}

        return json_format

    def read_all(self) -> Dict[str, Dict[str, float]]:
        """Read all measurements (pressure, altitude, temperature) from the sensor.

        Returns:
            Dictionary with all sensor readings
        """
        json_format = {}

        try:
            if not self._is_testing and self._sensor is not None:
                # Read from real sensor
                try:
                    pressure = round(self._sensor.pressure, 2)
                    altitude = round(self._sensor.altitude, 2)
                    temperature = round(self._sensor.temperature, 2)

                    json_format[self._type] = {
                        f"{self._name}_pressure": pressure,
                        f"{self._name}_altitude": altitude,
                        f"{self._name}_temperature": temperature
                    }

                    print(
                        f"[MPL3115A2] Read all actual sensor values - P: {pressure} hPa, A: {altitude} m, T: {temperature} C")

                except Exception as e:
                    # Error reading sensor, return None values instead of simulated values
                    json_format[self._type] = {
                        f"{self._name}_pressure": None,
                        f"{self._name}_altitude": None,
                        f"{self._name}_temperature": None
                    }
                    print(f"[MPL3115A2] Error reading real sensor: {str(e)}, returning None values")
            else:
                # We're in a test environment or sensor initialization failed
                # Only use simulated values in testing environment
                if self._is_testing:
                    simulated_values = self._get_simulated_values()
                    json_format[self._type] = {
                        f"{self._name}_pressure": simulated_values['pressure'],
                        f"{self._name}_altitude": simulated_values['altitude'],
                        f"{self._name}_temperature": simulated_values['temperature']
                    }
                    print(f"[MPL3115A2] In testing environment, using simulated values")
                else:
                    # On real hardware but sensor failed to initialize
                    json_format[self._type] = {
                        f"{self._name}_pressure": None,
                        f"{self._name}_altitude": None,
                        f"{self._name}_temperature": None
                    }
                    print(f"[MPL3115A2] Sensor initialization failed on real hardware, returning None values")

        except Exception as e:
            print(f"[MPL3115A2] Critical error reading sensor {self._name}: {str(e)}")
            json_format[self._type] = {
                f"{self._name}_pressure": None,
                f"{self._name}_altitude": None,
                f"{self._name}_temperature": None
            }

        return json_format

    @property
    def name(self) -> str:
        return self._name

    @property
    def pin(self) -> int:
        """Return SDA pin for compatibility with ISensor interface."""
        return self._sda_pin

    @property
    def sda_pin(self) -> int:
        return self._sda_pin

    @property
    def scl_pin(self) -> int:
        return self._scl_pin

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