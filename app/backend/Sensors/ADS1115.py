import os
import random
from typing import Dict, Optional

from app.backend.Dataclasses.Config import ADS1115Config
from app.backend.Providers.gpio_provider import gpio
from app.backend.Interfaces.ISensor import ISensor


class ADS1115(ISensor):
    """Implementation of the ADS1115 current sensor using I2C interface."""

    def __init__(self, config: ADS1115Config):
        """Initialize the ADS1115 current sensor."""

        self._type = 'ADS1115'
        self._name = config.name
        self._sda_pin = config.SDA
        self._scl_pin = config.SCL
        self._pin = config.read_pin
        self._min_value = config.min_value
        self._max_value = config.max_value
        self._unit = config.unit
        self._config_voltage_offset = config.voltage_offset
        self._is_testing = self._detect_testing_environment()
        self._last_reading = None
        self._ads = None

        # ADS1115 configuration
        self._i2c_address = 0x48  # Default I2C address
        self._gain = 1  # Programmable gain (±4.096V range)
        self._data_rate = 128  # 128 SPS (samples per second)

        # Current sensor calibration parameters
        # These would need to be calibrated for your specific current sensor
        self._voltage_offset = 1.65 # Offset voltage (V) - typically Vcc/2
        self._sensitivity = 0.1  # Sensitivity (V/A) - depends on current sensor model

        if not self._is_testing:
            try:
                import board
                import busio
                import adafruit_ads1x15.ads1115 as ADS
                from adafruit_ads1x15.analog_in import AnalogIn

                # Create I2C bus
                i2c = busio.I2C(board.SCL, board.SDA)

                # Create ADS1115 object
                self._ads = ADS.ADS1115(i2c, address=self._i2c_address)
                self._ads.gain = self._gain
                self._ads.data_rate = self._data_rate

                # Create analog input channel
                if self._pin == 0:
                    self._channel = AnalogIn(self._ads, ADS.P0)
                elif self._pin == 1:
                    self._channel = AnalogIn(self._ads, ADS.P1)
                elif self._pin == 2:
                    self._channel = AnalogIn(self._ads, ADS.P2)
                elif self._pin == 3:
                    self._channel = AnalogIn(self._ads, ADS.P3)
                else:
                    raise ValueError(f"Invalid ADS1115 channel: {self._pin}. Must be 0-3.")

                print(
                    f"[ADS1115] Successfully initialized on I2C address 0x{self._i2c_address:02X}, channel A{self._pin}")

            except ImportError:
                print("[ADS1115] Adafruit CircuitPython libraries not found, falling back to simulated values.")
                self._is_testing = True
            except Exception as e:
                print(f"[ADS1115] Failed to initialize ADS1115: {e}, falling back to simulated values.")
                self._is_testing = True

        self.initialize()

    def _detect_testing_environment(self) -> bool:
        """Detect if we're in a testing environment based on GPIO provider.

        Returns:
            True if in testing environment, False if on real hardware
        """
        # Check if we're using the MockGPIO from gpio_provider
        from app.backend.Providers.gpio_provider import GPIO
        is_mock = hasattr(GPIO, '__name__') and GPIO.__name__ == 'MockGPIO'

        # Additional check for actual Raspberry Pi hardware and I2C interface
        is_not_pi = not (
                os.path.exists('/opt/vc/bin/') or
                os.path.exists('/sys/firmware/devicetree/base/model') or
                os.path.exists('/proc/device-tree/model') or
                os.path.exists('/dev/i2c-1')  # I2C interface exists
        )

        return is_mock or is_not_pi

    def initialize(self) -> None:
        """Initialize the sensor hardware."""
        gpio.setmode(gpio.BCM)
        print(
            f"[ADS1115] Initialized current sensor '{self._name}' on channel A{self._pin}, testing mode: {self._is_testing}")

    def _voltage_to_current(self, voltage: float) -> float:
        """Convert voltage reading to current value.

        Args:
            voltage: Voltage reading from ADS1115

        Returns:
            Current value in the specified unit
        """
        # Calculate current based on sensor characteristics
        # Current = (Voltage - Offset) / Sensitivity
        current = (voltage - self._voltage_offset) / self._sensitivity

        # Apply unit conversion if needed
        if self._unit.lower() == 'ma':
            current *= 1000  # Convert A to mA

        return current

    def _get_simulated_value(self) -> float:
        """Generate a simulated current sensor value with natural variation.

        Returns:
            Simulated current reading with realistic variation.
        """
        # Initialize with a reasonable current value
        if self._last_reading is None:
            if self._unit.lower() == 'ma':
                self._last_reading = 100.0  # 100mA
            else:
                self._last_reading = 0.1  # 0.1A

        # Apply small random variation (±5% of current value)
        variation_percent = random.uniform(-0.05, 0.05)
        variation = self._last_reading * variation_percent
        new_value = self._last_reading + variation

        # Add some occasional spikes to simulate real current behavior
        if random.random() < 0.05:  # 5% chance of spike
            spike = self._last_reading * random.uniform(0.1, 0.3)
            new_value += spike

        # Keep value within specified min and max bounds and above zero
        new_value = max(0, max(self._min_value, min(self._max_value, new_value)))
        self._last_reading = new_value

        return round(new_value, 3)  # 3 decimal places for current

    def read(self) -> Dict[str, Optional[float]]:
        """Read current from the ADS1115 sensor.

        Returns:
            Dictionary mapping sensor name to its current reading value with data source info
        """
        json_format = {}
        
        # Add data source metadata (backward compatible)
        data_source_key = f"{self._name}_data_source"

        try:
            if not self._is_testing:
                # Read from actual ADS1115 sensor
                try:
                    # Read voltage from the specified channel
                    raw_voltage = self._channel.voltage
                    
                    # Apply calibration offset
                    voltage = raw_voltage - self._config_voltage_offset

                    # Convert voltage to current
                    current = self._voltage_to_current(voltage)

                    json_format[self._type] = {
                        self._name: round(current, 3),
                        data_source_key: "real"
                    }
                    self._last_reading = current
                    print(f"[ADS1115] Read actual sensor value: {current} {self._unit} (raw: {raw_voltage:.3f}V, calibrated: {voltage:.3f}V, offset: {self._config_voltage_offset:.3f}V)")


                except Exception as e:
                    # Error reading sensor, return None instead of simulated value
                    json_format[self._type] = {
                        self._name: None,
                        data_source_key: "error"
                    }
                    print(f"[ADS1115] Error reading real sensor: {str(e)}, returning None")
            else:
                # We're in a test environment or sensor initialization failed
                # Only use simulated values in testing environment
                if self._is_testing:
                    value = self._get_simulated_value()
                    json_format[self._type] = {
                        self._name: value,
                        data_source_key: "test"
                    }
                    print(f"[ADS1115] In testing environment, using simulated value: {value} {self._unit}")
                else:
                    # On real hardware but sensor failed to initialize
                    json_format[self._type] = {
                        self._name: None,
                        data_source_key: "failed"
                    }
                    print(f"[ADS1115] Sensor initialization failed on real hardware, returning None")

        except Exception as e:
            print(f"[ADS1115] Critical error reading sensor {self._name}: {str(e)}")
            json_format[self._type] = {
                self._name: None,
                data_source_key: "error"
            }

        return json_format
