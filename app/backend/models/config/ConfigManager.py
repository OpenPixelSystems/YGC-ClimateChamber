import json
from pathlib import Path
from dataclasses import dataclass


@dataclass
class PIDConfig:
    """Configuration for PID controller parameters."""
    kp: float = 1.0
    ki: float = 0.0
    kd: float = 0.0
    read_delay: float = 2.0


class ConfigManager:
    """Centralized configuration management for the application."""

    def __init__(self, config_path="app/config/control_config.json"):
        self.config_path = Path(config_path)
        self.pid_config = PIDConfig()
        self.load_config()

    def load_config(self):
        """Load configuration from file."""
        try:
            with open(self.config_path, 'r') as f:
                config_data = json.load(f)

                # Load PID configuration
                self.pid_config.kp = float(config_data.get("kp", {}).get("value", 1.0))
                self.pid_config.ki = float(config_data.get("ki", {}).get("value", 0.0))
                self.pid_config.kd = float(config_data.get("kd", {}).get("value", 0.0))
                self.pid_config.read_delay = float(config_data.get("sensor_read_delay", {}).get("value", 2.0))

                print(f"\nConfigManager: Loaded PID config - kp={self.pid_config.kp}, "
                      f"ki={self.pid_config.ki}, kd={self.pid_config.kd}, "
                      f"read_delay={self.pid_config.read_delay}")
        except (FileNotFoundError, KeyError, json.JSONDecodeError, ValueError) as e:
            print(f"\nConfigManager: Error loading config: {str(e)}")
            print("Using default values")

    def save_config(self):
        """Save current configuration to file."""
        config_data = {
            "sensor_read_delay": {
                "name": "sensor_read_delay",
                "value": self.pid_config.read_delay,
                "unit": "seconds",
                "_comment": "Handles how fast temperature sensors are read out."
            },
            "kp": {
                "name": "kp",
                "value": self.pid_config.kp,
                "unit": "",
                "_comment": "Proportional control"
            },
            "ki": {
                "name": "ki",
                "value": self.pid_config.ki,
                "unit": "",
                "_comment": "Integral control"
            },
            "kd": {
                "name": "kd",
                "value": self.pid_config.kd,
                "unit": "",
                "_comment": "Differential control"
            }
        }

        try:
            with open(self.config_path, 'w') as f:
                json.dump(config_data, f, indent=2)
                print(f"\nConfigManager: Configuration saved to {self.config_path}")
        except (FileNotFoundError, PermissionError) as e:
            print(f"\nConfigManager: Error saving config: {str(e)}")