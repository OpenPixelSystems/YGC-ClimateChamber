import json
from app.backend.services.gpio_provider import gpio
from app.backend.services.sensors.DHT22 import DHT22_read
from app.backend.services.sensors.DS18B20 import DS18B20_read

class Sensor:
    def __init__(self, name, sensor_info):
        self._name = name
        self._type = sensor_info["type"]
        if self._type == "temperature" or self._type == "humidity":
            # Access the editable sub-dictionary for these values
            self._pin = sensor_info["editable"]["gpio_pin"]
            self.max_value = sensor_info["editable"]["max_temp"]
            self.min_value = sensor_info["editable"]["min_temp"]
            self.unit = sensor_info["unit"]
            self._initialise_sensor()

    def _initialise_sensor(self):
        gpio.setmode(gpio.BCM)
        gpio.setup(self._pin, gpio.IN)

    def read_sensor(self):
        if self._type == "temperature":
            return DS18B20_read(self)
        elif self._type == "humidity":
            return DHT22_read(self)
        else :
            return {}


class SensorReader:
    """Handles initialisation, reading and logging logic of all connected sensors """

    def __init__(self, mcu_config_data_path):
        self.listeners = []
        self.sensor_config = mcu_config_data_path
        self.sensor_list = []
        self.initialise()

    def initialise(self):
        """Load configuration from JSON file"""
        try:
            with open(self.sensor_config, 'r') as f:
                config_data = json.load(f)
                # Iterate through all sensors in the config
                for sensor_name, sensor_info in config_data.items():
                    # Skip comment keys
                    if sensor_name == "_comment":
                        continue
                    self.sensor_list.append(Sensor(sensor_name, sensor_info))
        except (FileNotFoundError, KeyError, json.JSONDecodeError, ValueError) as e:
            raise RuntimeError(f"Configuration error: {str(e)}")

    def subscribe(self, callback):
        self.listeners.append(callback)

    def unsubscribe(self, callback):
        if callback in self.listeners:
            self.listeners.remove(callback)

    def notify(self, data):
        for callback in self.listeners:
            callback(data)

    def read_sensors(self):
        sensor_readings = {}
        for sensor in self.sensor_list:
            sensor_readings.update(sensor.read_sensor())
        self.notify(sensor_readings)
        return sensor_readings