
from app.backend.Dataclasses.Config import McuConfig
from app.backend.Interfaces.ISensorReader import ISensorReader
from app.backend.Sensors.ADS1115 import ADS1115
from app.backend.Sensors.DS18B20 import DS18B20
from app.backend.Sensors.DS18B20Cluster import DS18B20Cluster
from app.backend.Sensors.MPL3115A2 import MPL3115A2
from app.backend.Services.Subscribe import Subscriptable


class SensorReader(ISensorReader, Subscriptable):
    """Handles initialisation, reading and logging logic of all connected Sensors """
    #TODO add reload functionality for when config file gets edited

    def __init__(self, mcu_config: McuConfig):
        super().__init__()
        self.sensor_list = []
        self.initialise(mcu_config)

    def initialise(self, mcu_config: McuConfig):
        """Initialize Sensors from McuConfig dataclass"""
        try:
            # Iterate through all Sensors in the config
            for sensor_config in mcu_config.sensors:
                # Create the appropriate sensor instance
                if sensor_config.type == "DS18B20":
                    existing_cluster = None
                    for sensor in self.sensor_list:
                        if isinstance(sensor, DS18B20Cluster) and sensor.group_name == sensor_config.group_name:
                            existing_cluster = sensor
                            break
                    if existing_cluster:
                        existing_cluster.append(sensor_config)
                    else:
                        self.sensor_list.append(DS18B20Cluster(sensor_config))
                elif sensor_config.type == "ADS1115":
                    self.sensor_list.append(ADS1115(sensor_config))
                elif sensor_config.type == "MPL3115A2":
                    self.sensor_list.append(MPL3115A2(sensor_config.name, sensor_config.SDA,sensor_config.SCL, sensor_config.min_value, sensor_config.max_value, sensor_config.unit))
        except Exception as e:
            raise RuntimeError(f"Configuration error: {str(e)}")

    """Iterate through all sensors and return their value in json format"""
    def read_sensors(self):
        sensor_readings = {}
        for sensor in self.sensor_list:
            reading = sensor.read()  # e.g., {'DS18B20': {'outside_on_device': 19.9}}

            for sensor_type, data in reading.items():
                if sensor_type not in sensor_readings:
                    sensor_readings[sensor_type] = {}

                sensor_readings[sensor_type].update(data)

        self.notify(sensor_readings)
        return sensor_readings

    def subscribe(self, callback):
        Subscriptable.subscribe(self,callback)