import os
import random
from typing import Dict, Optional, List

from app.backend.Dataclasses.Config import DS18B20Config
from app.backend.Providers.gpio_provider import gpio

from app.backend.Interfaces.ISensor import ISensor
from app.backend.Sensors.DS18B20 import DS18B20


class DS18B20Cluster(ISensor):
    def __init__(self, sensor_config: DS18B20Config):
        self.type = "DS18B20Cluster"
        self.sensor_location = sensor_config.sensor_location
        self._pin = sensor_config.gpio_pin
        self.sensors: Optional[List[ISensor]] = []
        self._is_testing = self._detect_testing_environment()
        self.initialize()
        self.append(sensor_config)

    def append(self, sensor_config: DS18B20Config):
        self.sensors.append(DS18B20(sensor_config, self._is_testing))

    def initialize(self) -> None:
        """Initialize the sensor hardware."""
        gpio.setmode(gpio.BCM)
        gpio.setup(self._pin, gpio.IN)
        print(
            f"[DS18B20Cluster] [{self.sensor_location}] Initialized sensor on pin {self._pin}, testing mode: {self._is_testing}"
        )

    def read(self) -> Dict[str, Optional[float]]:
        sensor_readings = {}
        for sensor in self.sensors:
            reading = (
                sensor.read()
            )  # e.g., {'sensor_name': {'sensor_value': 19.9, 'sensor_source': 'test'}}

            # With the new flat structure, we can directly merge the readings
            sensor_readings.update(reading)

        return sensor_readings

    @property
    def name(self) -> str:
        sensors_names = ""
        for sensor in self.sensors:
            sensors_names += sensor.name + " "
        return sensors_names

    def _detect_testing_environment(self) -> bool:
        """Detect if we're in a testing environment based on GPIO provider.

        Returns:
            True if in testing environment, False if on real hardware
        """
        # Check if we're using the MockGPIO from gpio_provider
        from app.backend.Providers.gpio_provider import GPIO

        is_mock = hasattr(GPIO, "__name__") and GPIO.__name__ == "MockGPIO"

        # Additional check for actual Raspberry Pi hardware
        is_not_pi = not (
            os.path.exists("/opt/vc/bin/")
            or os.path.exists("/sys/firmware/devicetree/base/model")
            or os.path.exists("/proc/device-tree/model")
            or os.path.exists("/sys/bus/w1/devices/")  # 1-Wire interface exists
        )

        return is_mock or is_not_pi
