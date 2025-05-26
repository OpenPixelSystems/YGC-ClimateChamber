from typing import Dict, Optional

from app.backend.Dataclasses.Config import SensorConfig
from app.backend.Interfaces.ISensor import ISensor
from app.backend.Sensors.ADS1115 import ADS1115
from app.backend.Sensors.DS18B20 import DS18B20



class Sensor(ISensor):
    """Factory class for creating sensor instances."""

    def __init__(self, sensor_config: SensorConfig):
        """Initialize a sensor based on the provided information.
        
        Args:
            name: Name of the sensor
            sensor_info: Dictionary containing sensor configuration
        """
        self._name = sensor_config.name
        self._type = sensor_config.type
        self._sensor: Optional[ISensor] = None

        if self._type in ["DS18B20", "DHT22", "ADS1115"]:
            # Access the editable sub-dictionary for these values
            pin = sensor_config.gpio_pin
            max_value = sensor_config.max_value
            min_value = sensor_config.min_value
            unit = sensor_config.unit

            # Create the appropriate sensor instance
            if self._type == "DS18B20":
                self._sensor = DS18B20(self._name, pin, min_value, max_value, unit)
            elif self._type == "ADS1115":
                self._sensor = ADS1115(self._name, pin, min_value, max_value, unit)

    def read_sensor(self) -> Dict[str, Optional[float]]:
        """Read the sensor value.
        
        Returns:
            Dictionary mapping sensor name to its reading value
        """
        if self._sensor is None:
            return {}
        return self._sensor.read()