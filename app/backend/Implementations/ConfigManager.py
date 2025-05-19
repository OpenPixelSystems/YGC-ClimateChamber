import json

from app.backend.Dataclasses.Config import ControlConfig, GraphConfig, McuConfig, SensorConfig, PeltierConfig
from app.backend.Interfaces.IConfigManager import IConfigManager


class ConfigManager(IConfigManager):
    """Centralized configuration management for the application."""
    def __init__(self, control_config_path, graph_config_path, mcu_config_path):
        self.control_config_path = control_config_path
        self.graph_config_path = graph_config_path
        self.mcu_config_path = mcu_config_path

        self._control_config = ControlConfig()
        self._graph_config = GraphConfig()
        self._mcu_config = McuConfig()

        self.__load_control_config()
        self.__load_graph_config()
        self.__load_mcu_config()

    @property
    def control_config(self) -> ControlConfig:
        return self._control_config

    @property
    def graph_config(self) -> GraphConfig:
        return self._graph_config

    @property
    def mcu_config(self) -> McuConfig:
        return self._mcu_config

    def __load_control_config(self):
        """Load configuration from file."""
        try:
            with open(self.control_config_path, 'r') as f:
                config_data = json.load(f)

                # Load PID configuration and set default if file is corrupted
                self._control_config.kp = float(config_data.get("kp", {}).get("editable", {}).get("value", 1.0))
                self._control_config.ki = float(config_data.get("ki", {}).get("editable", {}).get("value", 0.0))
                self._control_config.kd = float(config_data.get("kd", {}).get("editable", {}).get("value", 0.0))
                self._control_config.read_delay = float(
                    config_data.get("sensor_read_delay", {}).get("editable", {}).get("value", 2.0))

                print(f"[ConfigManager] [__load_control_config] Loaded PID config - kp={self._control_config.kp}, "
                      f"ki={self._control_config.ki}, kd={self._control_config.kd}, "
                      f"read_delay={self._control_config.read_delay}")
        except (FileNotFoundError, KeyError, json.JSONDecodeError, ValueError) as e:
            print(f"[ConfigManager] [__load_control_config] Error loading config: {str(e)}")
            print("Using default values")

    def __load_graph_config(self):
        """Load configuration from file."""
        try:
            with open(self.graph_config_path, 'r') as f:
                config_data = json.load(f)

                # Load PID configuration and set default if file is corrupted
                self._graph_config.max_points = int(config_data.get("max_points", {}).get("editable", {}).get("value", 1))
                self._graph_config.min_x = int(config_data.get("min_x", {}).get("editable", {}).get("value", 0))
                self._graph_config.min_y = float(config_data.get("min_y", {}).get("editable", {}).get("value", 0))
                self._graph_config.max_y = float(config_data.get("max_y", {}).get("editable", {}).get("value", 0.0))
                self._graph_config.max_rico = float(config_data.get("max_rico", {}).get("editable", {}).get("value", 0.0))

                print(f"[ConfigManager] [__load_graph_config] Loaded graph config - max_points={self._graph_config.max_points}, "
                      f"min_x={self._graph_config.min_x}, min_y={self._graph_config.min_y}, max_y={self._graph_config.max_y}, "
                      f"max_rico={self._graph_config.max_rico}")
        except (FileNotFoundError, KeyError, json.JSONDecodeError, ValueError) as e:
            print(f"[ConfigManager] [__load_graph_config] Error loading config: {str(e)}")
            print("Using default values")

    def __load_mcu_config(self):
        """Load MCU configuration from file."""
        try:
            with open(self.mcu_config_path, 'r') as f:
                config_data = json.load(f)

            sensors = []
            peltier_modules = []
            for key, value in config_data.items():
                # Ignore keys that start with '_' (comments)
                if key.startswith("_"):
                    continue
                if value["type"] == "temperature":
                    sensors.append(SensorConfig(
                        name=value["name"],
                        type=value["type"],
                        gpio_pin=value["editable"]["gpio_pin"],
                        max_temp=value["editable"]["max_temp"],
                        min_temp=value["editable"]["min_temp"],
                        unit=value["unit"]
                    ))
                elif value["type"] == "peltier":
                    peltier_modules.append(PeltierConfig(
                        name=value["name"],
                        type=value["type"],
                        gpio_pin_heating=value["editable"]["gpio_pin_heating"],
                        gpio_pin_cooling=value["editable"]["gpio_pin_cooling"],
                        gpio_pin_pwm=value["editable"]["gpio_pin_pwm"],
                        pwm_frequency=value["editable"]["pwm_frequency"],
                        max_temp=value["editable"]["max_temp"],
                        min_temp=value["editable"]["min_temp"]
                    ))

            self._mcu_config.sensors = sensors
            print(f"[ConfigManager] [__load_mcu_config] Loaded {len(sensors)} sensors/devices into MCU config.")
            self._mcu_config.peltierModules = peltier_modules
            print(f"[ConfigManager] [__load_mcu_config] Loaded {len(peltier_modules)} Peltier module(s) into MCU config.")
        except (FileNotFoundError, KeyError, json.JSONDecodeError, ValueError) as e:
            print(f"[ConfigManager] [__load_mcu_config] Error loading MCU config: {str(e)}")
            self._mcu_config.sensors = []

    def reload_config(self):
        """Reload all configurations from their respective files."""
        self.__load_control_config()
        self.__load_graph_config()
        self.__load_mcu_config()  # TODO: editing mcu config should only happen if there is no running cycle