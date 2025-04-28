import json
from pathlib import Path
from dataclasses import dataclass


@dataclass
class ControlConfig:
    """Configuration for PID controller parameters."""
    kp: float = 1.0
    ki: float = 0.0
    kd: float = 0.0
    read_delay: float = 2.0

@dataclass
class GraphConfig:
    """Configuration for graph control parameters."""
    max_points: int = 100
    min_x: int = 0
    min_y: float = -10
    max_y: float = 100
    max_rico: float = 10

@dataclass
class SensorConfig:
    name: str = ""
    type: str = ""
    gpio_pin: int = 1
    max_temp: float = 1
    min_temp: float = 1
    unit: str = ""

@dataclass
class McuConfig:
    sensors: list[SensorConfig] = None

class ConfigManager:
    """Centralized configuration management for the application."""

    def __init__(self, app_state):
        self.app_state = app_state
        self.control_config = ControlConfig()
        self.graph_config = GraphConfig()
        self.mcu_config = McuConfig()
        self.__load_control_config()
        self.__load_graph_config()
        self.__load_mcu_config()

    def __load_control_config(self):
        """Load configuration from file."""
        try:
            with open(self.app_state.control_config_path, 'r') as f:
                config_data = json.load(f)

                # Load PID configuration and set default if file is corrupted
                self.control_config.kp = float(config_data.get("kp", {}).get("editable", {}).get("value", 1.0))
                self.control_config.ki = float(config_data.get("ki", {}).get("editable", {}).get("value", 0.0))
                self.control_config.kd = float(config_data.get("kd", {}).get("editable", {}).get("value", 0.0))
                self.control_config.read_delay = float(
                    config_data.get("sensor_read_delay", {}).get("editable", {}).get("value", 2.0))

                print(f"\nConfigManager: Loaded PID config - kp={self.control_config.kp}, "
                      f"ki={self.control_config.ki}, kd={self.control_config.kd}, "
                      f"read_delay={self.control_config.read_delay}")
        except (FileNotFoundError, KeyError, json.JSONDecodeError, ValueError) as e:
            print(f"\nConfigManager: Error loading config: {str(e)}")
            print("Using default values")

    def __load_graph_config(self):
        """Load configuration from file."""
        try:
            with open(self.app_state.graph_config_path, 'r') as f:
                config_data = json.load(f)

                # Load PID configuration and set default if file is corrupted
                self.graph_config.max_points = int(config_data.get("max_points", {}).get("editable", {}).get("value", 1))
                self.graph_config.min_x = int(config_data.get("min_x", {}).get("editable", {}).get("value", 0))
                self.graph_config.min_y = float(config_data.get("min_y", {}).get("editable", {}).get("value", 0))
                self.graph_config.max_y = float(config_data.get("max_y", {}).get("editable", {}).get("value", 0.0))
                self.graph_config.max_rico = float(config_data.get("max_rico", {}).get("editable", {}).get("value", 0.0))

                print(f"\nConfigManager: Loaded graph config - max_points={self.graph_config.max_points}, "
                      f"min_x={self.graph_config.min_x}, min_y={self.graph_config.min_y}, max_y={self.graph_config.max_y}, "
                      f"max_rico={self.graph_config.max_rico}")
        except (FileNotFoundError, KeyError, json.JSONDecodeError, ValueError) as e:
            print(f"\nConfigManager: Error loading config: {str(e)}")
            print("Using default values")

    def __load_mcu_config(self):
        """Load MCU configuration from file."""
        try:
            with open(self.app_state.mcu_config_path, 'r') as f:
                config_data = json.load(f)

            sensors = []
            for key, value in config_data.items():
                # Ignore keys that start with '_' (comments)
                if key.startswith("_"):
                    continue
                sensors.append(SensorConfig(
                    name=value["name"],
                    type=value["type"],
                    gpio_pin=value["editable"]["gpio_pin"],
                    max_temp=value["editable"]["max_temp"],
                    min_temp=value["editable"]["min_temp"],
                    unit=value["unit"]
                ))

            self.mcu_config.sensors = sensors
            print(f"\nConfigManager: Loaded {len(sensors)} sensors/devices into MCU config.")
        except (FileNotFoundError, KeyError, json.JSONDecodeError, ValueError) as e:
            print(f"\nConfigManager: Error loading MCU config: {str(e)}")
            self.mcu_config.sensors = []

    def reload_config(self):
        self.__load_control_config()
        self.__load_graph_config()
        self.__load_mcu_config()
