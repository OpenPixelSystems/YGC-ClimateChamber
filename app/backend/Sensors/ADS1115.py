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

        self.type = "ADS1115"
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
        self._i2c_address = (
            config.i2c_address if config.i2c_address is not None else 0x48
        )  # Use config address or default
        self._gain = 1  # Programmable gain (±4.096V range)
        self._data_rate = 128  # 128 SPS (samples per second)

        # Current sensor calibration parameters
        # These need to be calibrated for your specific current sensor
        # Common current sensors:
        # - ACS712-5A:  185 mV/A, offset ~2.5V (for 5V supply) or ~1.65V (for 3.3V)
        # - ACS712-20A: 100 mV/A, offset ~2.5V (for 5V supply) or ~1.65V (for 3.3V)
        # - ACS712-30A: 66 mV/A,  offset ~2.5V (for 5V supply) or ~1.65V (for 3.3V)
        # - Hall effect: 20-100 mV/A typically

        # Default values - CALIBRATED FROM FIELD DATA
        # Based on actual measurements: zero current ~1.66V, sensitivity varies by sensor
        self._voltage_offset = 1.66  # Offset voltage (V) - voltage at 0A (was 1.65)
        self._sensitivity = (
            0.2  # Sensitivity (V/A) - will be overridden per sensor (was 1.44)
        )

        # Use config voltage offset if provided (this overrides the calculated current)
        # Note: config.voltage_offset is applied to raw voltage, not current calculation

        # Override sensitivity and offset based on sensor name (from calibration data)
        # Final calibration values from field testing - all sensors now have positive sensitivity
        sensor_calibration = {
            "R_IS_1_Current_sensor": {
                "sensitivity": 0.047,
                "offset": 1.661,
                "inverted": False,
            },
            "L_IS_1_Current_sensor": {
                "sensitivity": 0.829,
                "offset": 1.642,
                "inverted": False,
            },
            "R_IS_2_Current_sensor": {
                "sensitivity": 0.005,
                "offset": 1.661,
                "inverted": False,
            },
            "L_IS_2_Current_sensor": {
                "sensitivity": 0.040,
                "offset": 1.668,
                "inverted": False,
            },  # Updated offset from 0A measurement
        }

        # Apply sensor-specific calibration
        self._inverted_polarity = False

        # First, try to use calibration values from config file
        if (
            hasattr(config, "calibrated_sensitivity")
            and config.calibrated_sensitivity is not None
        ):
            self._sensitivity = config.calibrated_sensitivity
            print(
                f"[ADS1115] Using config calibrated sensitivity {self._sensitivity:.3f}V/A for {self._name}"
            )

        if (
            hasattr(config, "calibrated_offset")
            and config.calibrated_offset is not None
        ):
            self._voltage_offset = config.calibrated_offset
            print(
                f"[ADS1115] Using config calibrated offset {self._voltage_offset:.3f}V for {self._name}"
            )

        # Fallback to hardcoded calibration values if not in config
        elif self._name in sensor_calibration:
            cal = sensor_calibration[self._name]
            self._sensitivity = cal["sensitivity"]
            self._voltage_offset = cal["offset"]
            self._inverted_polarity = cal["inverted"]
            print(
                f"[ADS1115] Using hardcoded calibrated values for {self._name}: sensitivity={self._sensitivity:.3f}V/A, offset={self._voltage_offset:.3f}V, inverted={self._inverted_polarity}"
            )

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
                    raise ValueError(
                        f"Invalid ADS1115 channel: {self._pin}. Must be 0-3."
                    )

                print(
                    f"[ADS1115] Successfully initialized on I2C address 0x{self._i2c_address:02X}, channel A{self._pin}"
                )

            except ImportError:
                print(
                    "[ADS1115] Adafruit CircuitPython libraries not found, falling back to simulated values."
                )
                self._is_testing = True
            except Exception as e:
                print(
                    f"[ADS1115] Failed to initialize ADS1115: {e}, falling back to simulated values."
                )
                self._is_testing = True

        self.initialize()

    def _detect_testing_environment(self) -> bool:
        """Detect if we're in a testing environment based on GPIO provider.

        Returns:
            True if in testing environment, False if on real hardware
        """
        # Check if we're using the MockGPIO from gpio_provider
        from app.backend.Providers.gpio_provider import GPIO

        is_mock = hasattr(GPIO, "__name__") and GPIO.__name__ == "MockGPIO"

        # Additional check for actual Raspberry Pi hardware and I2C interface
        is_not_pi = not (
            os.path.exists("/opt/vc/bin/")
            or os.path.exists("/sys/firmware/devicetree/base/model")
            or os.path.exists("/proc/device-tree/model")
            or os.path.exists("/dev/i2c-1")  # I2C interface exists
        )

        return is_mock or is_not_pi

    def initialize(self) -> None:
        """Initialize the sensor hardware."""
        gpio.setmode(gpio.BCM)
        print(
            f"[ADS1115] Initialized current sensor '{self._name}' on channel A{self._pin}, testing mode: {self._is_testing}"
        )

    def _voltage_to_current(self, voltage: float) -> float:
        """Convert voltage reading to current value.

        Args:
            voltage: Voltage reading from ADS1115

        Returns:
            Current value in the specified unit
        """
        # Calculate current based on sensor characteristics
        # Current = (Voltage - Offset) / Sensitivity
        voltage_diff = voltage - self._voltage_offset

        # Handle inverted polarity sensors
        if hasattr(self, "_inverted_polarity") and self._inverted_polarity:
            voltage_diff = -voltage_diff  # Invert the voltage difference

        current = voltage_diff / self._sensitivity

        # Ensure current is always positive (absolute value)
        current = abs(current)

        # Apply unit conversion if needed
        if self._unit.lower() == "ma":
            current *= 1000  # Convert A to mA

        return current

    def _get_simulated_value(self) -> float:
        """Generate a simulated current sensor value with natural variation.

        Returns:
            Simulated current reading with realistic variation.
        """
        # Initialize with a reasonable current value
        if self._last_reading is None:
            if self._unit.lower() == "ma":
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
            Dictionary mapping sensor name to sensor_value and sensor_source
        """
        json_format = {self._name: {"sensor_value": None, "sensor_source": "unknown"}}

        try:
            if not self._is_testing:
                # Read from actual ADS1115 sensor
                try:
                    # Read voltage from the specified channel
                    raw_voltage = self._channel.voltage

                    # Apply calibration offset (this is for voltage correction, not current calculation)
                    voltage = raw_voltage - self._config_voltage_offset

                    # Convert voltage to current
                    current = self._voltage_to_current(voltage)

                    json_format[self._name]["sensor_value"] = round(current, 3)
                    json_format[self._name]["sensor_source"] = "real"
                    self._last_reading = current

                    # Detailed debug information for calibration
                    print(
                        f"[ADS1115] {self._name}: Raw={raw_voltage:.3f}V, Corrected={voltage:.3f}V, Current={current:.3f}{self._unit}"
                    )
                    print(
                        f"[ADS1115] Calibration: offset={self._voltage_offset:.3f}V, sensitivity={self._sensitivity:.3f}V/A, config_offset={self._config_voltage_offset:.3f}V"
                    )

                except Exception as e:
                    # Error reading sensor, return None instead of simulated value
                    json_format[self._name]["sensor_value"] = None
                    json_format[self._name]["sensor_source"] = "error"
                    print(
                        f"[ADS1115] Error reading real sensor: {str(e)}, returning None"
                    )
            else:
                # We're in a test environment or sensor initialization failed
                # Only use simulated values in testing environment
                if self._is_testing:
                    value = self._get_simulated_value()
                    json_format[self._name]["sensor_value"] = value
                    json_format[self._name]["sensor_source"] = "test"
                    print(
                        f"[ADS1115] In testing environment, using simulated value: {value} {self._unit}"
                    )
                else:
                    # On real hardware but sensor failed to initialize
                    json_format[self._name]["sensor_value"] = None
                    json_format[self._name]["sensor_source"] = "failed"
                    print(
                        f"[ADS1115] Sensor initialization failed on real hardware, returning None"
                    )

        except Exception as e:
            print(f"[ADS1115] Critical error reading sensor {self._name}: {str(e)}")
            json_format[self._name]["sensor_value"] = None
            json_format[self._name]["sensor_source"] = "error"

        return json_format

    def calibrate_current_sensor(
        self, actual_current_amps: float, measured_voltage: float = None
    ):
        """Helper method to calibrate the current sensor.

        Usage:
        1. Measure actual current with multimeter
        2. Note the voltage reading from ADS1115
        3. Call this method to calculate correct sensitivity

        Args:
            actual_current_amps: The actual current measured with multimeter (in Amps)
            measured_voltage: The voltage reading from ADS1115 (if None, reads current voltage)
        """
        if measured_voltage is None:
            if self._is_testing:
                print("[ADS1115] Cannot calibrate in testing mode - need real hardware")
                return
            try:
                measured_voltage = self._channel.voltage - self._config_voltage_offset
            except Exception as e:
                print(f"[ADS1115] Error reading voltage for calibration: {e}")
                return

        print(f"\n[ADS1115] CALIBRATION DATA:")
        print(f"  Measured voltage: {measured_voltage:.3f}V")
        print(f"  Actual current: {actual_current_amps:.3f}A")
        print(f"  Current offset: {self._voltage_offset:.3f}V")

        # Handle zero current case (for offset calibration)
        if abs(actual_current_amps) < 0.01:  # Very close to zero current
            print(f"  Zero current detected - this is for offset calibration")
            print(f"  Current offset: {self._voltage_offset:.3f}V")
            print(f"  Measured voltage at 0A: {measured_voltage:.3f}V")
            print(
                f"  Voltage difference: {abs(measured_voltage - self._voltage_offset):.3f}V"
            )

            if (
                abs(measured_voltage - self._voltage_offset) > 0.1
            ):  # Significant offset error
                print(f"\nSUGGESTED OFFSET FIX:")
                print(
                    f"  Consider changing self._voltage_offset from {self._voltage_offset:.3f}V to {measured_voltage:.3f}V"
                )
            else:
                print(f"  Offset looks reasonable (difference < 0.1V)")

            return self._voltage_offset  # Return current offset

        # Calculate sensitivity for non-zero current
        voltage_above_offset = measured_voltage - self._voltage_offset
        calculated_sensitivity = voltage_above_offset / actual_current_amps

        print(f"  Voltage above offset: {voltage_above_offset:.3f}V")
        print(f"  Calculated sensitivity: {calculated_sensitivity:.3f}V/A")
        print(f"  Current sensitivity: {self._sensitivity:.3f}V/A")

        print(f"\nSUGGESTED SENSITIVITY FIX:")
        print(
            f"  Change self._sensitivity from {self._sensitivity:.3f} to {calculated_sensitivity:.3f}"
        )

        return calculated_sensitivity
