from app.backend.Interfaces.IConfigManager import IConfigManager
from app.backend.Interfaces.IGuardingService import IGuardingService
from app.backend.Interfaces.ISensorReader import ISensorReader
from app.backend.Technical.Logging import LoggingMixin


class GuardingService(IGuardingService, LoggingMixin):
    def __init__(self, sensor_reader: ISensorReader, config_manager: IConfigManager):
        super().__init__()
        self.stop_steering_current = False
        self.stop_steering_temperature = False
        self.sensor_reader = sensor_reader
        self.config_manager = config_manager
        self.critical_sensors = []
        self.get_critical_sensors()
        self.sensor_reader.subscribe(self.monitor_system)

    def get_critical_sensors(self):
        for sensor in self.config_manager.mcu_config.sensors:
            if sensor.critical:
                self.critical_sensors.append(sensor)

    def monitor_system(self, sensor_data):
        self.monitor_temperature(sensor_data["DS18B20"])
        self.monitor_current(sensor_data["ADS1115"])

    def monitor_temperature(self, temperature_data):
        self.print("[GuardingService] [monitor_temperature]", temperature_data)
        self.stop_steering_temperature = False

        for sensor_name, temperature in temperature_data.items():
            for sensor in self.critical_sensors:
                if sensor.name == sensor_name:
                    if temperature is None:
                        self.print(
                            f'[GuardingService][monitor_temperature] value missing for sensor {sensor_name}')
                        self.stop_steering_current = True
                        continue
                    if temperature > sensor.max_value:
                        self.print(
                            f'[GuardingService][monitor_temperature] value for sensor {sensor_name} above threshold limits')
                        self.stop_steering_temperature = True

    def monitor_current(self, current_data):
        self.print("[GuardingService] [monitor_temperature]", current_data)
        self.stop_steering_current = False

        for sensor_name, current in current_data.items():
            for sensor in self.critical_sensors:
                if sensor.name == sensor_name:
                    if current is None:
                        self.print(
                            f'[GuardingService][monitor_current] value missing for sensor {sensor_name}')
                        self.stop_steering_current = True
                        continue
                    if current > sensor.max_value:
                        self.print(
                            f'[GuardingService][monitor_current] value for sensor {sensor_name} above threshold limits')
                        self.stop_steering_current = True

    def get_guarding_state(self):
        return self.stop_steering_temperature or self.stop_steering_current