from app.backend.Implementations.Sensor import Sensor
from app.backend.Dataclasses.Config import McuConfig
from app.backend.Interfaces.ISensorReader import ISensorReader
from app.backend.Interfaces.ISubscribe import ISubscriptable
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
                if sensor_config.type == "temperature":
                    self.sensor_list.append(Sensor(sensor_config.name, {
                        "type": sensor_config.type,
                        "editable": {
                            "gpio_pin": sensor_config.gpio_pin,
                            "max_temp": sensor_config.max_temp,
                            "min_temp": sensor_config.min_temp
                        },
                        "unit": sensor_config.unit
                    }))
        except Exception as e:
            raise RuntimeError(f"Configuration error: {str(e)}")

    def read_sensors(self):
        sensor_readings = {}
        for sensor in self.sensor_list:
            sensor_readings.update(sensor.read_sensor())
        self.notify(sensor_readings)
        return sensor_readings