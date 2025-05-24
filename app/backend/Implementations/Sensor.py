from typing import Dict, Optional
from app.backend.Interfaces.ISensor import ISensor
from app.backend.Sensors.ADS1115 import ADS1115
from app.backend.Sensors.DS18B20 import DS18B20


class Sensor:
    """Factory class for creating sensor instances."""

    def __init__(self, name: str, sensor_info: Dict):
        """Initialize a sensor based on the provided information.
        
        Args:
            name: Name of the sensor
            sensor_info: Dictionary containing sensor configuration
        """
        self._name = name
        self._type = sensor_info["type"]
        self._control_sensor = True #TODO only control sensors should be used to regulate climate
        self._sensor: Optional[ISensor] = None

        if self._type in ["DS18B20", "DHT22", "ADS1115"]:
            # Access the editable sub-dictionary for these values
            pin = sensor_info["editable"]["gpio_pin"]
            max_value = sensor_info["editable"]["max_temp"]
            min_value = sensor_info["editable"]["min_temp"]
            unit = sensor_info["unit"]

            # Create the appropriate sensor instance
            if self._type == "DS18B20":
                self._sensor = DS18B20(name, pin, min_value, max_value, unit)
            elif self._type == "ADS1115":
                self._sensor = ADS1115(name, pin, min_value, max_value, unit)

    def read_sensor(self) -> Dict[str, Optional[float]]:
        """Read the sensor value.
        
        Returns:
            Dictionary mapping sensor name to its reading value
        """
        if self._sensor is None:
            return {}
        return self._sensor.read()