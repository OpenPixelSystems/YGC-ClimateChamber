import os
import random
import math
from typing import Dict, Optional

from app.backend.Dataclasses.Config import NTCConfig
from app.backend.Providers.gpio_provider import gpio
from app.backend.Interfaces.ISensor import ISensor
from app.backend.Services.TemperatureSimulation import get_temperature_simulation_service


class NTCTemperatureSensor(ISensor):
    """Implementation of NTC temperature sensor using ADS1115 ADC and voltage divider."""

    def __init__(self, config: NTCConfig):
        """Initialize the NTC temperature sensor."""

        self.type = 'NTC'
        self.name = config.name
        self.sensor_location = config.sensor_location
        self._sda_pin = config.SDA
        self._scl_pin = config.SCL
        self._pin = config.read_pin
        self._min_value = config.min_value
        self._max_value = config.max_value
        self._unit = config.unit
        self._is_testing = self._detect_testing_environment()
        self._last_reading = None
        self._ads = None

        # ADS1115 configuration
        self._i2c_address = config.i2c_address if config.i2c_address is not None else 0x48
        self._gain = 1  # Programmable gain (±4.096V range)
        self._data_rate = 128  # 128 SPS (samples per second)

        # NTC thermistor parameters
        self._beta = config.beta_coefficient  # Beta coefficient (K)
        self._r_ref = config.reference_resistance  # Reference resistance (ohms)
        self._v_ref = config.reference_voltage  # Reference voltage (V)
        self._t_ref = 25.0  # Reference temperature (°C)
        self._t_ref_k = self._t_ref + 273.15  # Reference temperature (K)

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
                    f"[NTC] Successfully initialized on I2C address 0x{self._i2c_address:02X}, channel A{self._pin}")

            except ImportError:
                print("[NTC] Adafruit CircuitPython libraries not found, falling back to simulated values.")
                self._is_testing = True
            except Exception as e:
                print(f"[NTC] Failed to initialize ADS1115: {e}, falling back to simulated values.")
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
            f"[NTC] Initialized NTC temperature sensor '{self.name}' on channel A{self._pin}, testing mode: {self._is_testing}")

    def _voltage_to_temperature(self, voltage: float) -> float:
        """Convert voltage reading to temperature using NTC thermistor equation.

        Args:
            voltage: Voltage reading from ADS1115

        Returns:
            Temperature value in Celsius
        """
        # Calculate resistance of NTC thermistor from voltage divider
        # Assuming voltage divider: V_ref -> R_ref -> ADC_input -> NTC -> GND
        # V_adc = V_ref * R_ntc / (R_ref + R_ntc)
        # Solving for R_ntc: R_ntc = (V_adc * R_ref) / (V_ref - V_adc)
        
        if voltage >= self._v_ref:
            # Avoid division by zero or negative values
            voltage = self._v_ref - 0.001  # Small offset to prevent issues
            
        if voltage <= 0:
            voltage = 0.001  # Small positive value to prevent issues
            
        r_ntc = (voltage * self._r_ref) / (self._v_ref - voltage)
        
        # Use Steinhart-Hart approximation with Beta parameter
        # 1/T = 1/T_ref + (1/B) * ln(R/R_ref)
        # Where T is in Kelvin
        
        # Calculate temperature in Kelvin
        temp_k = 1.0 / ((1.0 / self._t_ref_k) + (1.0 / self._beta) * math.log(r_ntc / self._r_ref))
        
        # Convert to Celsius
        temp_c = temp_k - 273.15
        
        return temp_c

    def _get_simulated_value(self) -> float:
        """Generate a simulated temperature sensor value based on PID control output and physics.

        Returns:
            Simulated temperature reading with realistic physics-based behavior.
        """
        try:
            # Use the physics-based temperature simulation service
            simulation_service = get_temperature_simulation_service()
            simulated_temp = simulation_service.get_simulated_temperature(
                sensor_name=self.name,  # Use self.name instead of self._name
                min_temp=self._min_value,
                max_temp=self._max_value
            )
            self._last_reading = simulated_temp
            return round(simulated_temp, 2)  # 2 decimal places for temperature
        except Exception as e:
            print(f"[NTCTemperatureSensor] Warning: Temperature simulation failed, using fallback: {e}")

            # Fallback to old simple simulation if service fails
            if self._last_reading is None:
                self._last_reading = 25.0  # 25°C

            # Apply small random variation (±2°C)
            variation = random.uniform(-2.0, 2.0)
            new_value = self._last_reading + (variation * 0.1)  # Small gradual changes

            # Add some occasional temperature changes to simulate real behavior
            if random.random() < 0.02:  # 2% chance of larger change
                change = random.uniform(-5.0, 5.0)
                new_value += change

            # Keep value within specified min and max bounds
            new_value = max(self._min_value, min(self._max_value, new_value))
            self._last_reading = new_value

            return round(new_value, 2)  # 2 decimal places for temperature

    def read(self) -> Dict[str, Optional[float]]:
        """Read temperature from the NTC sensor via ADS1115.

        Returns:
            Dictionary mapping sensor name to sensor_value and sensor_source
        """
        json_format = {self.name: {"sensor_value": None, "sensor_source": "unknown"}}

        try:
            if not self._is_testing:
                # Read from actual ADS1115 sensor
                try:
                    # Read voltage from the specified channel
                    voltage = self._channel.voltage

                    # Convert voltage to temperature
                    temperature = self._voltage_to_temperature(voltage)

                    json_format[self.name]["sensor_value"] = round(temperature, 2)
                    json_format[self.name]["sensor_source"] = "real"
                    self._last_reading = temperature
                    
                    # Debug information
                    print(f"[NTC] {self.name}: Voltage={voltage:.3f}V, Temperature={temperature:.2f}°C")

                except Exception as e:
                    # Error reading sensor, return None instead of simulated value
                    json_format[self.name]["sensor_value"] = None
                    json_format[self.name]["sensor_source"] = "error"
                    print(f"[NTC] Error reading real sensor: {str(e)}, returning None")
            else:
                # We're in a test environment or sensor initialization failed
                # Only use simulated values in testing environment
                if self._is_testing:
                    value = self._get_simulated_value()
                    json_format[self.name]["sensor_value"] = value
                    json_format[self.name]["sensor_source"] = "test"
                    print(f"[NTC] In testing environment, using simulated value: {value} {self._unit}")
                else:
                    # On real hardware but sensor failed to initialize
                    json_format[self.name]["sensor_value"] = None
                    json_format[self.name]["sensor_source"] = "failed"
                    print(f"[NTC] Sensor initialization failed on real hardware, returning None")

        except Exception as e:
            print(f"[NTC] Critical error reading sensor {self.name}: {str(e)}")
            json_format[self.name]["sensor_value"] = None
            json_format[self.name]["sensor_source"] = "error"

        return json_format
    
    def calibrate_ntc_sensor(self, actual_temperature_c: float, measured_voltage: float = None):
        """Helper method to calibrate the NTC temperature sensor.
        
        Usage:
        1. Measure actual temperature with reference thermometer
        2. Note the voltage reading from ADS1115
        3. Call this method to calculate correct beta coefficient or reference resistance
        
        Args:
            actual_temperature_c: The actual temperature measured with reference thermometer (in Celsius)
            measured_voltage: The voltage reading from ADS1115 (if None, reads current voltage)
        """
        if measured_voltage is None:
            if self._is_testing:
                print("[NTC] Cannot calibrate in testing mode - need real hardware")
                return
            try:
                measured_voltage = self._channel.voltage
            except Exception as e:
                print(f"[NTC] Error reading voltage for calibration: {e}")
                return
        
        print(f"\n[NTC] CALIBRATION DATA:")
        print(f"  Measured voltage: {measured_voltage:.3f}V")
        print(f"  Actual temperature: {actual_temperature_c:.2f}°C")
        print(f"  Reference voltage: {self._v_ref:.1f}V")
        print(f"  Reference resistance: {self._r_ref:.0f}Ω")
        
        # Calculate NTC resistance from voltage divider
        if measured_voltage >= self._v_ref:
            measured_voltage = self._v_ref - 0.001
        if measured_voltage <= 0:
            measured_voltage = 0.001
            
        r_ntc = (measured_voltage * self._r_ref) / (self._v_ref - measured_voltage)
        print(f"  Calculated NTC resistance: {r_ntc:.0f}Ω")
        
        # Calculate beta coefficient based on actual temperature
        actual_temp_k = actual_temperature_c + 273.15
        
        # B = ln(R/R_ref) / (1/T - 1/T_ref)
        calculated_beta = math.log(r_ntc / self._r_ref) / ((1.0 / actual_temp_k) - (1.0 / self._t_ref_k))
        
        print(f"  Current beta: {self._beta:.0f}K")
        print(f"  Calculated beta: {calculated_beta:.0f}K")
        
        print(f"\nSUGGESTED BETA COEFFICIENT FIX:")
        print(f"  Change beta_coefficient from {self._beta:.0f} to {calculated_beta:.0f}")
        
        return calculated_beta