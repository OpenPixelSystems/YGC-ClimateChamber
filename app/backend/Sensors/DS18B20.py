import random
import time
import threading
from typing import Dict, Optional

from app.backend.Dataclasses.Config import DS18B20Config
from app.backend.Interfaces.ISensor import ISensor


class DS18B20(ISensor):
    """Simplified DS18B20 temperature sensor implementation using w1thermsensor in production."""

    def __init__(self, sensor_config: DS18B20Config, is_testing: bool):
        """Initialize the DS18B20 sensor.

        Args:
            sensor_config: Configuration object containing sensor parameters
            is_testing: Whether to use simulated values for testing
        """
        self._type = 'DS18B20'
        self._name = sensor_config.name
        self._serial_code = sensor_config.rom_address
        self._pin = sensor_config.gpio_pin
        self._min_value = sensor_config.min_value
        self._max_value = sensor_config.max_value
        self._unit = sensor_config.unit
        self._is_testing = is_testing
        self._last_reading = None
        self._last_successful_reading = None
        self._consecutive_failures = 0
        self._max_consecutive_failures = 3
        self._read_timeout = 3.0  # 3 second timeout for sensor reads

        # Production sensor object (only created when not testing)
        self._sensor = None
        self._full_rom_address = f"28-{self._serial_code}"

        # Import state tracking
        self._w1thermsensor_available = False
        self._Unit = None  # Store Unit class reference

        self.initialize()

    def initialize(self) -> None:
        """Initialize the sensor hardware and verify connection."""
        print(f"[DS18B20] [initialize] Initializing DS18B20 with code: {self._full_rom_address}")

        if self._is_testing:
            print(f"[DS18B20] [initialize] Testing mode enabled - using simulated values")
            return

        # Try to import w1thermsensor once during initialization
        try:
            from w1thermsensor import W1ThermSensor, Sensor, Unit
            self._w1thermsensor_available = True
            self._Unit = Unit  # Store reference for later use

        except ImportError:
            print(f"[DS18B20] [initialize] ERROR: w1thermsensor library not available")
            print(f"[DS18B20] [initialize] Install with: pip install w1thermsensor")
            return

        # Try to create sensor object with specific sensor ID
        try:
            self._sensor = W1ThermSensor(sensor_type=Sensor.DS18B20, sensor_id=self._serial_code)

            # Test read to verify sensor is working
            test_temp = self._sensor.get_temperature(Unit.DEGREES_C)

            print(f"[DS18B20] [initialize] SUCCESS: DS18B20 sensor '{self._full_rom_address}' connected")
            print(f"[DS18B20] [initialize] Current temperature: {test_temp}°C")
            print(f"[DS18B20] [initialize] Note: Resolution should be set via /etc/rc.local for optimal performance")

        except Exception as e:
            print(f"[DS18B20] [initialize] ERROR: Failed to initialize sensor '{self._full_rom_address}': {str(e)}")
            self._sensor = None

            # Try to list available sensors for troubleshooting
            try:
                available_sensors = W1ThermSensor.get_available_sensors([Sensor.DS18B20])
                if available_sensors:
                    print(f"[DS18B20] [initialize] Available DS18B20 sensors:")
                    for sensor in available_sensors:
                        print(f"[DS18B20] [initialize]   - {sensor.id}")
                    print(f"[DS18B20] [initialize] Please check if ROM address '{self._serial_code}' is correct")
                else:
                    print(f"[DS18B20] [initialize]   - No DS18B20 sensors found")
                    print(f"[DS18B20] [initialize] Check sensor wiring and 1-Wire configuration")
            except Exception as list_error:
                print(f"[DS18B20] [initialize] Could not list available sensors: {str(list_error)}")
                print(
                    f"[DS18B20] [initialize] Make sure 1-Wire is enabled in /boot/config.txt with 'dtoverlay=w1-gpio'")

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
        new_value = max(self._min_value, min(self._max_value + 1, new_value))
        self._last_reading = new_value

        return round(new_value, 1)

    def _read_sensor_with_timeout(self) -> Optional[float]:
        """Read sensor with timeout to prevent system stalls.
        
        Returns:
            Temperature reading or None if timeout/error occurred
        """
        if not (self._sensor and self._w1thermsensor_available):
            return None
            
        result = [None]
        exception_info = [None]
        
        def read_thread():
            try:
                result[0] = self._sensor.get_temperature(self._Unit.DEGREES_C)
            except Exception as e:
                exception_info[0] = e
        
        thread = threading.Thread(target=read_thread, daemon=True)
        thread.start()
        thread.join(timeout=self._read_timeout)
        
        if thread.is_alive():
            print(f"[DS18B20] Sensor {self._full_rom_address} read timed out after {self._read_timeout}s")
            return None
            
        if exception_info[0]:
            print(f"[DS18B20] Sensor {self._full_rom_address} read failed: {exception_info[0]}")
            return None
            
        return result[0]

    def read(self) -> Dict[str, Dict[str, Optional[float]]]:
        """Read temperature from sensor or return simulated value in testing mode.

        Returns:
            Dictionary mapping sensor name to sensor_value and sensor_source
        """
        json_format = {self._name: {"sensor_value": None, "sensor_source": "unknown"}}

        try:
            if self._is_testing:
                # Testing mode - use simulated values
                value = self._get_simulated_value()
                json_format[self._name]["sensor_value"] = value
                json_format[self._name]["sensor_source"] = "test"
                print(f"[DS18B20] Testing mode - simulated value for {self._full_rom_address}: {value} {self._unit}")
            else:
                # Production mode - read from real sensor with timeout
                temp_c = self._read_sensor_with_timeout()
                
                if temp_c is not None:
                    # Successful read
                    rounded_temp = round(temp_c, 1)
                    json_format[self._name]["sensor_value"] = rounded_temp
                    json_format[self._name]["sensor_source"] = "real"
                    self._last_reading = rounded_temp
                    self._last_successful_reading = rounded_temp
                    self._consecutive_failures = 0
                    print(f"[DS18B20] Read sensor {self._full_rom_address}: {rounded_temp} {self._unit}")
                else:
                    # Failed read - increment failure counter
                    self._consecutive_failures += 1
                    print(f"[DS18B20] Failed to read sensor {self._full_rom_address} (failure #{self._consecutive_failures})")
                    
                    # Use fallback strategy based on failure count
                    if self._consecutive_failures <= self._max_consecutive_failures and self._last_successful_reading is not None:
                        # Use last successful reading as fallback
                        fallback_value = self._last_successful_reading
                        json_format[self._name]["sensor_value"] = fallback_value
                        json_format[self._name]["sensor_source"] = "fallback"
                        print(f"[DS18B20] Using fallback value for {self._full_rom_address}: {fallback_value} {self._unit}")
                    else:
                        # Too many consecutive failures, return None
                        print(f"[DS18B20] Max consecutive failures ({self._max_consecutive_failures}) reached for {self._full_rom_address}, returning None")
                        json_format[self._name]["sensor_value"] = None
                        json_format[self._name]["sensor_source"] = "failed"

        except Exception as e:
            print(f"[DS18B20] Critical error reading sensor {self._name} ({self._full_rom_address}): {str(e)}")
            self._consecutive_failures += 1
            json_format[self._name]["sensor_source"] = "error"

        return json_format

    @property
    def name(self) -> str:
        return self._name