import os
import random
from typing import Dict, Optional
from app.backend.Providers.gpio_provider import gpio
from app.backend.Interfaces.ISensor import ISensor


class ADS1115(ISensor):
    """Implementation of the ADS1115 current sensor using I2C interface."""

    def __init__(self, name: str, pin: int, min_value: float, max_value: float, unit: str):
        """Initialize the ADS1115 current sensor.

        Args:
            name: Name of the sensor
            pin: Analog channel number (0-3 for ADS1115)
            min_value: Minimum expected current value
            max_value: Maximum expected current value
            unit: Unit of measurement (should be 'A' for amperes or 'mA' for milliamperes)
        """
        self._type = 'ADS1115'
        self._name = name
        self._pin = pin  # This represents the analog channel (A0-A3)
        self._min_value = min_value
        self._max_value = max_value
        self._unit = unit
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
            Dictionary mapping sensor name to its current reading value
        """
        json_format = {}

        try:
            if not self._is_testing and self._ads is not None:
                # Read from actual ADS1115 sensor
                try:
                    # Read voltage from the specified channel
                    voltage = self._channel.voltage

                    # Convert voltage to current
                    current = self._voltage_to_current(voltage)

                    # Validate reading is within bounds
                    if self._min_value <= current <= self._max_value:
                        json_format[self._type] = {self._name: round(current, 3)}
                        self._last_reading = current
                        print(f"[ADS1115] Read actual sensor value: {current} {self._unit} (voltage: {voltage:.3f}V)")
                    else:
                        # Reading out of bounds, use simulated value
                        value = self._get_simulated_value()
                        json_format[self._type] = {self._name: value}
                        print(
                            f"[ADS1115] Reading out of bounds ({current} {self._unit}), using simulated value: {value} {self._unit}")

                except Exception as e:
                    # Error reading sensor, use simulated value
                    value = self._get_simulated_value()
                    json_format[self._type] = {self._name: value}
                    print(f"[ADS1115] Error reading real sensor: {str(e)}, using simulated value: {value} {self._unit}")
            else:
                # We're in a test environment or sensor initialization failed
                value = self._get_simulated_value()
                json_format[self._type] = {self._name: value}
                print(f"[ADS1115] In testing environment, using simulated value: {value} {self._unit}")

        except Exception as e:
            print(f"[ADS1115] Critical error reading sensor {self._name}: {str(e)}")
            json_format[self._type] = {self._name: None}

        return json_format

    def set_calibration(self, voltage_offset: float, sensitivity: float) -> None:
        """Set calibration parameters for the current sensor.

        Args:
            voltage_offset: Offset voltage in volts (typically Vcc/2 for bidirectional sensors)
            sensitivity: Sensitivity in V/A (depends on current sensor model)
        """
        self._voltage_offset = voltage_offset
        self._sensitivity = sensitivity
        print(f"[ADS1115] Updated calibration: offset={voltage_offset}V, sensitivity={sensitivity}V/A")

    def set_gain(self, gain: int) -> None:
        """Set the programmable gain amplifier setting.

        Args:
            gain: Gain setting (1=±4.096V, 2=±2.048V, 4=±1.024V, 8=±0.512V, 16=±0.256V)
        """
        if not self._is_testing and self._ads is not None:
            self._ads.gain = gain
            self._gain = gain
            print(f"[ADS1115] Set gain to {gain}")

    def get_raw_voltage(self) -> Optional[float]:
        """Get raw voltage reading from the ADS1115.

        Returns:
            Raw voltage reading or None if in testing mode
        """
        if not self._is_testing and self._ads is not None:
            try:
                return self._channel.voltage
            except Exception as e:
                print(f"[ADS1115] Error reading raw voltage: {e}")
                return None
        return None

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

    @property
    def i2c_address(self) -> int:
        return self._i2c_address

    @property
    def channel(self) -> int:
        """Return the analog channel being used (0-3)."""
        return self._pin

    @property
    def calibration_info(self) -> Dict[str, float]:
        """Return current calibration parameters."""
        return {
            'voltage_offset': self._voltage_offset,
            'sensitivity': self._sensitivity,
            'gain': self._gain
        }