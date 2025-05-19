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
class PeltierConfig:
    name: str = ""
    type: str = ""
    gpio_pin_heating: int = 1
    gpio_pin_cooling: int = 1
    gpio_pin_pwm: int = 1
    pwm_frequency: int = 1
    max_temp: float = 1
    min_temp: float = 1

@dataclass
class McuConfig:
    sensors: list[SensorConfig] = None
    peltierModules: list[PeltierConfig] = None