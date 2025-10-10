import json

from app.backend.Dataclasses.Config import (
    ControlConfig,
    GraphConfig,
    McuConfig,
    PeltierConfig,
    MPL3115A2Config,
    ADS1115Config,
    NTCConfig,
    DS18B20Config,
    FanConfig,
    RelayConfig,
)
from app.backend.Interfaces.IConfigManager import IConfigManager
from app.backend.Technical.Logging import LoggingMixin


class ConfigManager(IConfigManager, LoggingMixin):
    """Centralized configuration management for the application."""

    def __init__(self, control_config_path, graph_config_path, mcu_config_path):
        super().__init__()
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
            with open(self.control_config_path, "r") as f:
                config_data = json.load(f)

                # Load PID configuration and set default if file is corrupted
                self._control_config.kp = float(
                    config_data.get("kp", {}).get("editable", {}).get("value", 1.0)
                )
                self._control_config.ki = float(
                    config_data.get("ki", {}).get("editable", {}).get("value", 0.0)
                )
                self._control_config.kd = float(
                    config_data.get("kd", {}).get("editable", {}).get("value", 0.0)
                )
                self._control_config.read_delay = float(
                    config_data.get("sensor_read_delay", {})
                    .get("editable", {})
                    .get("value", 2.0)
                )

                self.print(
                    f"[ConfigManager] [__load_control_config] Loaded PID config - kp={self._control_config.kp}, "
                    f"ki={self._control_config.ki}, kd={self._control_config.kd}, "
                    f"read_delay={self._control_config.read_delay}"
                )
        except (FileNotFoundError, KeyError, json.JSONDecodeError, ValueError) as e:
            self.print_error(
                f"[ConfigManager] [__load_control_config] Error loading config: {str(e)}"
            )
            self.print_error("Using default values")

    def __load_graph_config(self):
        """Load configuration from file."""
        try:
            with open(self.graph_config_path, "r") as f:
                config_data = json.load(f)

                # Load PID configuration and set default if file is corrupted
                self._graph_config.max_points = int(
                    config_data.get("max_points", {})
                    .get("editable", {})
                    .get("value", 1)
                )
                self._graph_config.min_x = int(
                    config_data.get("min_x", {}).get("editable", {}).get("value", 0)
                )
                self._graph_config.min_y = float(
                    config_data.get("min_y", {}).get("editable", {}).get("value", 0)
                )
                self._graph_config.max_y = float(
                    config_data.get("max_y", {}).get("editable", {}).get("value", 0.0)
                )
                self._graph_config.max_rico = float(
                    config_data.get("max_rico", {})
                    .get("editable", {})
                    .get("value", 0.0)
                )
                self._graph_config.max_rico_heating = float(
                    config_data.get("max_rico_heating", {})
                    .get("editable", {})
                    .get("value", 10.0)
                )
                self._graph_config.max_rico_cooling = float(
                    config_data.get("max_rico_cooling", {})
                    .get("editable", {})
                    .get("value", 10.0)
                )
                self._graph_config.heating_curve_factor = float(
                    config_data.get("heating_curve_factor", {})
                    .get("editable", {})
                    .get("value", 0.6)
                )
                self._graph_config.cooling_curve_factor = float(
                    config_data.get("cooling_curve_factor", {})
                    .get("editable", {})
                    .get("value", 0.7)
                )

                self.print(
                    f"[ConfigManager] [__load_graph_config] Loaded graph config - max_points={self._graph_config.max_points}, "
                    f"min_x={self._graph_config.min_x}, min_y={self._graph_config.min_y}, max_y={self._graph_config.max_y}, "
                    f"max_rico={self._graph_config.max_rico}, max_rico_heating={self._graph_config.max_rico_heating}, "
                    f"max_rico_cooling={self._graph_config.max_rico_cooling}, heating_curve_factor={self._graph_config.heating_curve_factor}, "
                    f"cooling_curve_factor={self._graph_config.cooling_curve_factor}"
                )
        except (FileNotFoundError, KeyError, json.JSONDecodeError, ValueError) as e:
            self.print_error(
                f"[ConfigManager] [__load_graph_config] Error loading config: {str(e)}"
            )
            self.print_error("Using default values")

    def __load_mcu_config(self):
        """Load MCU configuration from file."""
        try:
            with open(self.mcu_config_path, "r") as f:
                config_data = json.load(f)

            sensors = []
            peltier_modules = []
            fan_modules = []
            relay_modules = []
            for key, value in config_data.items():
                # Ignore keys that start with '_' (comments)
                if key.startswith("_"):
                    continue
                if value["type"] == "DS18B20":
                    sensors.append(
                        DS18B20Config(
                            name=value["name"],
                            type=value["type"],
                            sensor_location=value["editable"].get(
                                "sensor_location", "default"
                            ),
                            rom_address=value["editable"]["rom_address"],
                            gpio_pin=value["editable"]["gpio_pin"],
                            max_value=value["editable"]["max_value"],
                            min_value=value["editable"]["min_value"],
                            critical=value["editable"]["safety_critical"] == 1,
                            unit=value["unit"],
                        )
                    )
                elif value["type"] == "ADS1115":
                    sensors.append(
                        ADS1115Config(
                            name=value["name"],
                            type=value["type"],
                            SDA=value["editable"]["SDA"],
                            SCL=value["editable"]["SCL"],
                            read_pin=value["editable"]["read_pin"],
                            max_value=value["editable"]["max_value"],
                            min_value=value["editable"]["min_value"],
                            critical=value["editable"]["safety_critical"] == 1,
                            unit=value["unit"],
                            voltage_offset=value["editable"]["voltage_offset"],
                            calibrated_sensitivity=value["editable"].get(
                                "calibrated_sensitivity"
                            ),
                            calibrated_offset=value["editable"].get(
                                "calibrated_offset"
                            ),
                            i2c_address=int(value["editable"].get("i2c_address"), 16),
                        )
                    )
                elif value["type"] == "NTC":
                    sensors.append(
                        NTCConfig(
                            name=value["name"],
                            type=value["type"],
                            SDA=value["editable"]["SDA"],
                            SCL=value["editable"]["SCL"],
                            sensor_location=value["editable"].get(
                                "sensor_location", "default"
                            ),
                            read_pin=value["editable"]["read_pin"],
                            max_value=value["editable"]["max_value"],
                            min_value=value["editable"]["min_value"],
                            critical=value["editable"]["safety_critical"] == 1,
                            unit=value["unit"],
                            i2c_address=int(value["editable"].get("i2c_address"), 16),
                            beta_coefficient=value["editable"].get(
                                "beta_coefficient", 3600.0
                            ),
                            reference_resistance=value["editable"].get(
                                "reference_resistance", 10000.0
                            ),
                            reference_voltage=value["editable"].get(
                                "reference_voltage", 3.3
                            ),
                        )
                    )
                elif value["type"] == "MPL3115A2":
                    sensors.append(
                        MPL3115A2Config(
                            name=value["name"],
                            type=value["type"],
                            SDA=value["editable"]["SDA"],
                            SCL=value["editable"]["SCL"],
                            max_value=value["editable"]["max_value"],
                            min_value=value["editable"]["min_value"],
                            critical=value["editable"]["safety_critical"] == 1,
                            unit=value["unit"],
                        )
                    )
                elif value["type"] == "peltier":
                    peltier_modules.append(
                        PeltierConfig(
                            name=value["name"],
                            driver_type=value["editable"]["driver_type"],
                            RPWM=value["editable"]["RPWM"],
                            LPWM=value["editable"]["LPWM"],
                            R_EN=value["editable"]["R_EN"],
                            L_EN=value["editable"]["L_EN"],
                            PWM_FREQUENCY=value["editable"]["PWM_FREQUENCY"],
                            Duty_cycle_limit=value["editable"]["Duty cycle limit"],
                        )
                    )
                elif value["type"] == "fanModule":
                    fan_modules.append(
                        FanConfig(
                            name=value["name"],
                            type=value["type"],
                            EN=value["editable"]["EN"],
                        )
                    )
                elif value["type"] == "relayModule":
                    relay_modules.append(
                        RelayConfig(
                            name=value["editable"]["name"],
                            gpio_pin=value["editable"]["gpio_pin"],
                        )
                    )

            for sensor in sensors:
                print("[ConfigManager] [__load_mcu_config] " + str(sensor))
            self._mcu_config.sensors = sensors
            self.print(
                f"[ConfigManager] [__load_mcu_config] Loaded {len(sensors)} sensors/devices into MCU config."
            )

            for peltier in peltier_modules:
                print("[ConfigManager] [__load_mcu_config]" + str(peltier))
            self._mcu_config.peltierModules = peltier_modules
            self.print(
                f"[ConfigManager] [__load_mcu_config] Loaded {len(peltier_modules)} Peltier module(s) into MCU config."
            )

            for fan in fan_modules:
                print("[ConfigManager] [__load_mcu_config] " + str(fan))
            self._mcu_config.fanModules = fan_modules
            self.print(
                f"[ConfigManager] [__load_mcu_config] Loaded {len(fan_modules)} fan module(s) into MCU config."
            )

            for relay in relay_modules:
                print("[ConfigManager] [__load_mcu_config] " + str(relay))
            self._mcu_config.relayModules = relay_modules
            self.print(
                f"[ConfigManager] [__load_mcu_config] Loaded {len(relay_modules)} relay module(s) into MCU config."
            )

        except (FileNotFoundError, KeyError, json.JSONDecodeError, ValueError) as e:
            self.print_error(
                f"[ConfigManager] [__load_mcu_config] Error loading MCU config: {str(e)}"
            )
            self._mcu_config.sensors = []
