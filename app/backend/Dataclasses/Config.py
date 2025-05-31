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
    type: str = ""
    RPWM: int = None
    LPWM: int = None
    R_EN: int = None
    L_EN: int = None
    PWM_FREQUENCY: float = None
    Duty_cycle_limit: int = None

@dataclass
class McuConfig:
    sensors: list[SensorConfig] = None
    peltierModules: list[PeltierConfig] = None