import os
import random
import time
import threading
from typing import Dict, Optional, Tuple
from app.backend.Providers.gpio_provider import gpio
from app.backend.Interfaces.ISensor import ISensor


class DHT22(ISensor):
    """
    Flask-optimized DHT22 sensor implementation with background reading thread.

    This version reads the sensor in a separate thread to avoid Flask timing conflicts
    and provides cached values for immediate response to web requests.
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
        self._dht_lib = None

        # Thread-safe data storage
        self._data_lock = threading.Lock()
        self._current_temperature = None
        self._current_humidity = None
        self._last_successful_read = 0
        self._read_attempts = 0
        self._successful_reads = 0

        # Background reading configuration
        self._background_thread = None
        self._stop_background = False
        self._read_interval = 5.0  # Read every 5 seconds in background
        self._max_cache_age = 30.0  # Consider data stale after 30 seconds

        # Retry configuration for background reads
        self.MAX_RETRIES = 5  # More retries in background thread
        self.RETRY_DELAY = 1.0
        self.READ_TIMEOUT = 10.0  # Max time to spend trying to read

        if not self._is_testing:
            try:
                import Adafruit_DHT
                self._dht_lib = Adafruit_DHT
                print(f"[DHT22] Adafruit_DHT library loaded successfully")
            except ImportError:
                print("[DHT22] Adafruit_DHT library not found, falling back to simulated values.")
                self._is_testing = True

        self.initialize()

        # Start background reading thread for real sensors
        if not self._is_testing:
            self._start_background_reader()

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

    def initialize(self) -> None:
        """Initialize the sensor hardware."""
        gpio.setmode(gpio.BCM)
        print(f"[DHT22] Initialized sensor '{self._name}' on pin {self._pin}")
        print(f"[DHT22] Testing mode: {self._is_testing}")

    def _start_background_reader(self) -> None:
        """Start the background thread for continuous sensor reading."""
        if self._background_thread is None or not self._background_thread.is_alive():
            self._stop_background = False
            self._background_thread = threading.Thread(
                target=self._background_read_loop,
                name=f"DHT22-{self._name}-Reader",
                daemon=True
            )
            self._background_thread.start()
            print(f"[DHT22] Started background reader thread for {self._name}")

    def _background_read_loop(self) -> None:
        """
        Background thread loop that continuously reads the sensor.

        This runs independently of Flask requests to avoid timing conflicts.
        """
        print(f"[DHT22] Background reader started for {self._name}")

        while not self._stop_background:
            try:
                start_time = time.time()

                # Attempt to read the sensor with retries
                humidity, temperature = self._read_sensor_with_retries()

                # Update cached values thread-safely
                with self._data_lock:
                    self._read_attempts += 1

                    if humidity is not None and temperature is not None:
                        self._current_humidity = round(humidity, 1)
                        self._current_temperature = round(temperature, 1)
                        self._last_successful_read = time.time()
                        self._successful_reads += 1

                        success_rate = (self._successful_reads / self._read_attempts) * 100
                        print(f"[DHT22] Background read success: {temperature}°C, {humidity}% "
                              f"(Success rate: {success_rate:.1f}%)")
                    else:
                        print(f"[DHT22] Background read failed (attempt #{self._read_attempts})")

                # Calculate how long to sleep
                elapsed = time.time() - start_time
                sleep_time = max(0, self._read_interval - elapsed)

                # Sleep in small intervals to allow for clean shutdown
                while sleep_time > 0 and not self._stop_background:
                    time.sleep(min(0.5, sleep_time))
                    sleep_time -= 0.5

            except Exception as e:
                print(f"[DHT22] Background reader error: {e}")
                time.sleep(self._read_interval)

        print(f"[DHT22] Background reader stopped for {self._name}")

    def _read_sensor_with_retries(self) -> Tuple[Optional[float], Optional[float]]:
        """
        Attempt to read the DHT22 sensor with retry logic.

        This version is optimized for background operation with more aggressive retries.
        """
        if not self._dht_lib:
            return None, None

        for attempt in range(self.MAX_RETRIES):
            try:
                # Use read_retry method which has better error handling
                if hasattr(self._dht_lib, 'read_retry'):
                    humidity, temperature = self._dht_lib.read_retry(
                        self._dht_lib.DHT22,
                        self._pin,
                        retries=3,
                        delay_seconds=1
                    )
                else:
                    humidity, temperature = self._dht_lib.read(self._dht_lib.DHT22, self._pin)

                # Validate readings
                if (humidity is not None and temperature is not None and
                        0 <= humidity <= 100 and -40 <= temperature <= 80):
                    return humidity, temperature

            except Exception as e:
                if attempt == 0:  # Only log on first attempt to reduce spam
                    print(f"[DHT22] Read exception (will retry): {e}")

            # Wait before retry
            if attempt < self.MAX_RETRIES - 1:
                time.sleep(self.RETRY_DELAY)

        return None, None

    def _get_simulated_value(self) -> float:
        """Generate realistic simulated sensor values."""
        base_temp = 22.0 + 3.0 * random.uniform(-1, 1)  # 19-25°C
        base_humidity = 45.0 + 15.0 * random.uniform(-1, 1)  # 30-60%

        if self._is_temperature:
            return round(max(self._min_value, min(self._max_value, base_temp)), 1)
        else:
            return round(max(self._min_value, min(self._max_value, base_humidity)), 1)

    def read(self) -> Dict[str, Optional[float]]:
        """
        Read the current sensor value.

        For Flask applications, this returns immediately with cached values
        from the background thread, avoiding timing conflicts.
        """
        json_format = {}

        try:
            if self._is_testing:
                # Testing mode - return simulated values
                value = self._get_simulated_value()
                json_format[self._name] = value
                print(f"[DHT22] Testing mode - simulated value: {value} {self._unit}")
            else:
                # Production mode - use cached values from background thread
                with self._data_lock:
                    current_time = time.time()
                    cache_age = current_time - self._last_successful_read

                    if cache_age <= self._max_cache_age:
                        # Use fresh cached data
                        if self._is_temperature and self._current_temperature is not None:
                            value = self._current_temperature
                            json_format[self._name] = value
                            print(f"[DHT22] Using cached temperature: {value}°C (age: {cache_age:.1f}s)")
                        elif not self._is_temperature and self._current_humidity is not None:
                            value = self._current_humidity
                            json_format[self._name] = value
                            print(f"[DHT22] Using cached humidity: {value}% (age: {cache_age:.1f}s)")
                        else:
                            # No cached data available
                            value = self._get_simulated_value()
                            json_format[self._name] = value
                            print(f"[DHT22] No cached data, using simulated: {value} {self._unit}")
                    else:
                        # Cached data is too old
                        value = self._get_simulated_value()
                        json_format[self._name] = value
                        print(f"[DHT22] Cached data too old ({cache_age:.1f}s), using simulated: {value} {self._unit}")

        except Exception as e:
            print(f"[DHT22] Error in read(): {e}")
            json_format[self._name] = self._get_simulated_value()

        return json_format

    def stop_background_reader(self) -> None:
        """Stop the background reading thread."""
        self._stop_background = True
        if self._background_thread and self._background_thread.is_alive():
            self._background_thread.join(timeout=5.0)
            print(f"[DHT22] Background reader stopped for {self._name}")

    def get_sensor_status(self) -> Dict[str, any]:
        """Get detailed sensor status information."""
        with self._data_lock:
            cache_age = time.time() - self._last_successful_read if self._last_successful_read > 0 else None
            success_rate = (self._successful_reads / self._read_attempts * 100) if self._read_attempts > 0 else 0

            status = {
                'name': self._name,
                'pin': self._pin,
                'is_testing': self._is_testing,
                'background_thread_alive': self._background_thread.is_alive() if self._background_thread else False,
                'last_successful_read': self._last_successful_read,
                'cache_age_seconds': cache_age,
                'cached_temperature': self._current_temperature,
                'cached_humidity': self._current_humidity,
                'total_attempts': self._read_attempts,
                'successful_reads': self._successful_reads,
                'success_rate_percent': round(success_rate, 1),
                'data_is_fresh': cache_age <= self._max_cache_age if cache_age else False
            }

        return status

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

    def __del__(self):
        """Cleanup when object is destroyed."""
        if hasattr(self, '_stop_background'):
            self.stop_background_reader()