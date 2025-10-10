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

        # Track detailed reasons for steering disable
        self.guarding_reasons = []
        self.last_violation_time = None

        self.get_critical_sensors()
        self.sensor_reader.subscribe(self.monitor_system)

    def get_critical_sensors(self):
        for sensor in self.config_manager.mcu_config.sensors:
            if sensor.type == "DS18B20Cluster":
                for DS18B20_sensor in sensor.sensors:
                    if DS18B20_sensor.critical:
                        self.critical_sensors.append(DS18B20_sensor)
            elif sensor.critical:
                self.critical_sensors.append(sensor)

    def monitor_system(self, sensor_data):
        # With the new flat structure, we need to filter sensors by type
        temperature_sensors = {}
        current_sensors = {}

        for sensor_name, sensor_info in sensor_data.items():
            if sensor_name == "_cache_info":
                continue
            if isinstance(sensor_info, dict) and "sensor_value" in sensor_info:
                # Check if this is a temperature sensor (DS18B20)
                for critical_sensor in self.critical_sensors:
                    if (
                        critical_sensor.name == sensor_name
                        and critical_sensor.type == "DS18B20"
                    ):
                        temperature_sensors[sensor_name] = sensor_info["sensor_value"]
                    elif (
                        critical_sensor.name == sensor_name
                        and critical_sensor.type == "ADS1115"
                    ):
                        current_sensors[sensor_name] = sensor_info["sensor_value"]

        self.monitor_temperature(temperature_sensors)
        self.monitor_current(current_sensors)

    def monitor_temperature(self, temperature_data):
        self.print("[GuardingService] [monitor_temperature]", temperature_data)
        self.stop_steering_temperature = False

        # Clear temperature-related reasons
        self.guarding_reasons = [
            r for r in self.guarding_reasons if not r["type"].startswith("temperature")
        ]

        for sensor_name, temperature in temperature_data.items():
            for critical_sensor in self.critical_sensors:
                if critical_sensor.name == sensor_name:
                    if temperature is None:
                        reason = {
                            "type": "temperature_missing",
                            "sensor": sensor_name,
                            "message": f"Temperature sensor {sensor_name} value missing",
                            "timestamp": self._get_current_timestamp(),
                        }
                        self.guarding_reasons.append(reason)
                        self.print(
                            f"[GuardingService][monitor_temperature] value missing for sensor {sensor_name}"
                        )
                        self.stop_steering_temperature = True
                        self.last_violation_time = self._get_current_timestamp()
                        continue
                    if temperature > critical_sensor.max_value:
                        reason = {
                            "type": "temperature_exceeded",
                            "sensor": sensor_name,
                            "value": temperature,
                            "max_value": critical_sensor.max_value,
                            "message": f"Temperature sensor {sensor_name} exceeded limit: {temperature}°C > {critical_sensor.max_value}°C",
                            "timestamp": self._get_current_timestamp(),
                        }
                        self.guarding_reasons.append(reason)
                        self.print(
                            f"[GuardingService][monitor_temperature] value for sensor {sensor_name} above threshold limits"
                        )
                        self.stop_steering_temperature = True
                        self.last_violation_time = self._get_current_timestamp()

    def monitor_current(self, current_data):
        self.print("[GuardingService] [monitor_current]", current_data)
        self.stop_steering_current = False

        # Clear current-related reasons
        self.guarding_reasons = [
            r for r in self.guarding_reasons if not r["type"].startswith("current")
        ]

        for sensor_name, current in current_data.items():
            for sensor in self.critical_sensors:
                if sensor.name == sensor_name:
                    if current is None:
                        reason = {
                            "type": "current_missing",
                            "sensor": sensor_name,
                            "message": f"Current sensor {sensor_name} value missing",
                            "timestamp": self._get_current_timestamp(),
                        }
                        self.guarding_reasons.append(reason)
                        self.print(
                            f"[GuardingService][monitor_current] value missing for sensor {sensor_name}"
                        )
                        self.stop_steering_current = True
                        self.last_violation_time = self._get_current_timestamp()
                        continue
                    if current > sensor.max_value:
                        reason = {
                            "type": "current_exceeded",
                            "sensor": sensor_name,
                            "value": current,
                            "max_value": sensor.max_value,
                            "message": f"Current sensor {sensor_name} exceeded limit: {current}A > {sensor.max_value}A",
                            "timestamp": self._get_current_timestamp(),
                        }
                        self.guarding_reasons.append(reason)
                        self.print(
                            f"[GuardingService][monitor_current] value for sensor {sensor_name} above threshold limits"
                        )
                        self.stop_steering_current = True
                        self.last_violation_time = self._get_current_timestamp()

    def get_guarding_state(self):
        return self.stop_steering_temperature or self.stop_steering_current

    def get_guarding_info(self):
        """Get detailed guarding information for frontend"""
        return {
            "is_guarding": self.get_guarding_state(),
            "reasons": self.guarding_reasons,
            "last_violation_time": self.last_violation_time,
            "stop_steering_temperature": self.stop_steering_temperature,
            "stop_steering_current": self.stop_steering_current,
        }

    def _get_current_timestamp(self):
        """Get current timestamp as ISO string"""
        from datetime import datetime

        return datetime.now().isoformat()
