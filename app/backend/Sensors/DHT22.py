import os
import random
import time
import subprocess
import threading
from typing import Dict, Optional, Tuple
from app.backend.Providers.gpio_provider import gpio
from app.backend.Interfaces.ISensor import ISensor


class DHT22(ISensor):
    """
    Flask-optimized DHT22 sensor using external process for reliable readings.

    This version uses a separate Python process to read the sensor, which is much
    more reliable than trying to do precise timing within a Flask application.
    """

    def __init__(self, name: str, pin: int, min_value: float, max_value: float, unit: str):
        """
        Initialize the DHT22 sensor.

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

        # Cache for storing readings
        self._data_lock = threading.Lock()
        self._cached_temperature = None
        self._cached_humidity = None
        self._last_read_time = 0
        self._cache_duration = 10.0  # Cache readings for 10 seconds

        # Statistics
        self._read_attempts = 0
        self._successful_reads = 0

        # Check for external sensor reading script
        self._external_reader_available = self._check_external_reader()

        if not self._is_testing and not self._external_reader_available:
            try:
                import Adafruit_DHT
                self._dht_lib = Adafruit_DHT
                print(f"[DHT22] Using Adafruit_DHT library (may be unreliable with Flask)")
            except ImportError:
                print("[DHT22] Adafruit_DHT library not found, falling back to simulated values.")
                self._is_testing = True

        self.initialize()

    def _detect_testing_environment(self) -> bool:
        """Detect if we're in a testing environment based on GPIO provider."""
        from app.backend.Providers.gpio_provider import GPIO
        is_mock = hasattr(GPIO, '__name__') and GPIO.__name__ == 'MockGPIO'

        is_not_pi = not (
                os.path.exists('/opt/vc/bin/') or
                os.path.exists('/sys/firmware/devicetree/base/model') or
                os.path.exists('/proc/device-tree/model')
        )

        return is_mock or is_not_pi

    def _check_external_reader(self) -> bool:
        """Check if external DHT22 reader script is available."""
        try:
            # Try to find the external reader script
            result = subprocess.run(['which', 'dht22_read'],
                                    capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                print(f"[DHT22] Found external dht22_read command")
                return True

            # Check for Python script in common locations
            script_paths = [
                '/usr/local/bin/dht22_reader.py',
                '/home/pi/dht22_reader.py',
                './dht22_reader.py'
            ]

            for path in script_paths:
                if os.path.exists(path):
                    print(f"[DHT22] Found external reader script: {path}")
                    return True

        except Exception as e:
            print(f"[DHT22] Error checking for external reader: {e}")

        return False

    def initialize(self) -> None:
        """Initialize the sensor hardware."""
        gpio.setmode(gpio.BCM)
        print(f"[DHT22] Initialized sensor '{self._name}' on pin {self._pin}")
        print(f"[DHT22] Testing mode: {self._is_testing}")
        print(f"[DHT22] External reader available: {self._external_reader_available}")

    def _read_with_external_process(self) -> Tuple[Optional[float], Optional[float]]:
        """
        Read sensor using external process for better reliability.

        This method spawns a separate Python process that's not affected by
        Flask's timing constraints.
        """
        try:
            # Create a simple external reading script on the fly
            script_content = f'''
import sys
try:
    import Adafruit_DHT
    humidity, temperature = Adafruit_DHT.read_retry(Adafruit_DHT.DHT22, {self._pin})
    if humidity is not None and temperature is not None:
        print(f"{{temperature:.2f}},{{humidity:.2f}}")
        sys.exit(0)
    else:
        sys.exit(1)
except ImportError:
    sys.exit(2)
except Exception as e:
    sys.exit(3)
'''

            # Write script to temporary file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(script_content)
                script_path = f.name

            try:
                # Run the external script with high priority
                result = subprocess.run([
                    'nice', '-n', '-10',  # Higher priority
                    'python3', script_path
                ], capture_output=True, text=True, timeout=15)

                if result.returncode == 0 and result.stdout.strip():
                    # Parse the output
                    temp_str, hum_str = result.stdout.strip().split(',')
                    temperature = float(temp_str)
                    humidity = float(hum_str)

                    # Validate readings
                    if 0 <= humidity <= 100 and -40 <= temperature <= 80:
                        return humidity, temperature

            finally:
                # Clean up temporary file
                try:
                    os.unlink(script_path)
                except:
                    pass

        except Exception as e:
            print(f"[DHT22] External process read failed: {e}")

        return None, None

    def _read_with_library(self) -> Tuple[Optional[float], Optional[float]]:
        """
        Fallback to reading with Adafruit_DHT library directly.

        This is less reliable with Flask but kept as fallback.
        """
        if not hasattr(self, '_dht_lib') or not self._dht_lib:
            return None, None

        try:
            # Try read_retry first (more reliable)
            if hasattr(self._dht_lib, 'read_retry'):
                humidity, temperature = self._dht_lib.read_retry(
                    self._dht_lib.DHT22, self._pin, retries=15, delay_seconds=2
                )
            else:
                humidity, temperature = self._dht_lib.read(self._dht_lib.DHT22, self._pin)

            if (humidity is not None and temperature is not None and
                    0 <= humidity <= 100 and -40 <= temperature <= 80):
                return humidity, temperature

        except Exception as e:
            print(f"[DHT22] Library read failed: {e}")

        return None, None

    def _get_simulated_value(self) -> float:
        """Generate realistic simulated sensor values."""
        # More realistic simulation with some persistence
        current_time = time.time()

        # Use time-based variation for more realistic simulation
        time_factor = (current_time % 3600) / 3600  # Hour cycle

        if self._is_temperature:
            base = 22.0 + 5.0 * (0.5 - time_factor)  # 17-27°C daily variation
            noise = random.uniform(-0.5, 0.5)
            value = base + noise
        else:
            base = 50.0 + 20.0 * time_factor  # 30-70% daily variation
            noise = random.uniform(-2.0, 2.0)
            value = base + noise

        return round(max(self._min_value, min(self._max_value, value)), 1)

    def _should_read_sensor(self) -> bool:
        """Check if we should attempt a fresh sensor read."""
        with self._data_lock:
            return (time.time() - self._last_read_time) >= self._cache_duration

    def _update_cache(self, humidity: float, temperature: float) -> None:
        """Update cached sensor values thread-safely."""
        with self._data_lock:
            self._cached_humidity = round(humidity, 1)
            self._cached_temperature = round(temperature, 1)
            self._last_read_time = time.time()
            self._successful_reads += 1

    def read(self) -> Dict[str, Optional[float]]:
        """
        Read the current sensor value with intelligent caching.

        Uses cached values when available, attempts fresh read when cache expires.
        """
        json_format = {}

        try:
            if self._is_testing:
                # Testing mode - return simulated values
                value = self._get_simulated_value()
                json_format[self._name] = value
                return json_format

            # Check if we should attempt a fresh read
            if self._should_read_sensor():
                print(f"[DHT22] Attempting fresh sensor read...")
                self._read_attempts += 1

                # Try external process first (most reliable)
                humidity, temperature = self._read_with_external_process()

                # Fall back to library if external process failed
                if humidity is None or temperature is None:
                    humidity, temperature = self._read_with_library()

                if humidity is not None and temperature is not None:
                    self._update_cache(humidity, temperature)
                    success_rate = (self._successful_reads / self._read_attempts) * 100
                    print(f"[DHT22] Fresh read success: {temperature}°C, {humidity}% "
                          f"(Success rate: {success_rate:.1f}%)")

            # Return cached or current value
            with self._data_lock:
                if self._is_temperature and self._cached_temperature is not None:
                    cache_age = time.time() - self._last_read_time
                    value = self._cached_temperature
                    print(f"[DHT22] Using cached temperature: {value}°C (age: {cache_age:.1f}s)")
                elif not self._is_temperature and self._cached_humidity is not None:
                    cache_age = time.time() - self._last_read_time
                    value = self._cached_humidity
                    print(f"[DHT22] Using cached humidity: {value}% (age: {cache_age:.1f}s)")
                else:
                    # No cached data available
                    value = self._get_simulated_value()
                    print(f"[DHT22] No cached data, using simulated: {value} {self._unit}")

                json_format[self._name] = value

        except Exception as e:
            print(f"[DHT22] Error in read(): {e}")
            json_format[self._name] = self._get_simulated_value()

        return json_format

    def force_read(self) -> Dict[str, Optional[float]]:
        """Force a fresh sensor read, ignoring cache."""
        with self._data_lock:
            self._last_read_time = 0  # Force cache expiry
        return self.read()

    def get_sensor_status(self) -> Dict[str, any]:
        """Get detailed sensor status information."""
        with self._data_lock:
            cache_age = time.time() - self._last_read_time if self._last_read_time > 0 else None
            success_rate = (self._successful_reads / self._read_attempts * 100) if self._read_attempts > 0 else 0

            return {
                'name': self._name,
                'pin': self._pin,
                'is_testing': self._is_testing,
                'external_reader_available': self._external_reader_available,
                'last_read_time': self._last_read_time,
                'cache_age_seconds': cache_age,
                'cached_temperature': self._cached_temperature,
                'cached_humidity': self._cached_humidity,
                'total_attempts': self._read_attempts,
                'successful_reads': self._successful_reads,
                'success_rate_percent': round(success_rate, 1),
                'cache_is_fresh': cache_age < self._cache_duration if cache_age else False
            }

    # Properties remain the same
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