from dataclasses import dataclass
from typing import List, Optional

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
class ISensorConfig:
    """Configuration for ISensor parameters."""
    name: str = ""
    type: str = ""
    max_value: float = None
    min_value: float = None
    unit: str = ""
    critical: bool = False


@dataclass
class DS18B20Config(ISensorConfig):
    """Configuration for DS18B20 parameters."""
    sensor_location: str = ""
    rom_address: str = ""
    gpio_pin: int = 4

@dataclass
class ADS1115Config(ISensorConfig):
    read_pin: int = None
    SDA: int = None
    SCL: int = None
    voltage_offset: float = 0.0
    calibrated_sensitivity: Optional[float] = None
    calibrated_offset: Optional[float] = None
    i2c_address: Optional[int] = None

@dataclass
class NTCConfig(ISensorConfig):
    read_pin: int = None
    SDA: int = None
    SCL: int = None
    sensor_location: str = ""
    i2c_address: Optional[int] = None
    beta_coefficient: float = 3600.0
    reference_resistance: float = 10000.0
    reference_voltage: float = 3.3

@dataclass
class MPL3115A2Config(ISensorConfig):
    SDA: int = None
    SCL: int = None

@dataclass
class SensorConfig:
    name: str = ""
    type: str = ""
    gpio_pin: int = None
    SDA: int = None
    SCL: int = None
    max_value: float = None
    min_value: float = None
    unit: str = ""
    critical: bool = False

@dataclass
class PeltierConfig:
    name: str = ""
    driver_type: str = ""
    RPWM: int = None
    LPWM: int = None
    R_EN: int = None
    L_EN: int = None
    PWM_FREQUENCY: float = None
    Duty_cycle_limit: int = None

@dataclass
class FanConfig:
    name: str = ""
    type: str = ""
    EN: int = None

@dataclass
class DriverConfig:
    name: str = ""
    type: str = ""
    EN: int = None

@dataclass
class RelayConfig:
    name: str = ""
    gpio_pin: int = None

@dataclass
class McuConfig:
    sensors: Optional[List[ISensorConfig]] = None
    peltierModules: Optional[List[PeltierConfig]] = None
    fanModules: Optional[List[FanConfig]] = None
    relayModules: Optional[List[RelayConfig]] = None