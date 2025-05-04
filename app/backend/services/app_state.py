from threading import Lock
from pathlib import Path
import os

_app_state = None

def get_app_state():
    global _app_state
    if _app_state is None:
        _app_state = AppState()  # or use a default config path
    return _app_state

class SingletonMeta(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]

class AppState(metaclass=SingletonMeta):
    def __init__(self):
        """Initializes instance variables (only runs once)."""
        # Shared storage between models, controllers and services
        self.desired_flow_graph = None
        self.start_time = None
        self.read_interval = 0.1
        self.provider_interval = 1

        # Paths
        self.config_dir = Path('app/backend/config')
        self.graph_config_path = self.config_dir / 'graph_config.json'
        self.control_config_path = self.config_dir / 'control_config.json'
        self.mcu_config_path = self.config_dir / 'raspberry_pi_config.json'

        # Create components using the factory
        """ Reader instance used to initialise and read sensors """
        self.sensor_reader = self._create_sensor_reader()
        """ Database instance used to log, retrieve and delete sensors """
        self.database = self._create_temperature_logger()
        """ Config manager instance """
        self.config_manager = self._create_config_manager()
        """ Climate chamber controller used to control Peltier elements based on sensor data and desired graph."""
        self.climate_chamber = self._create_climate_chamber()
        self.controller = self._create_controller()

    def _create_sensor_reader(self):
        """Factory method for creating the sensor reader."""
        from app.backend.services.SensorReader import SensorReader
        return SensorReader(self.mcu_config_path)

    def _create_temperature_logger(self):
        """Factory method for creating the temperature logger."""
        from database.TemperatureSensorLogger import TemperatureSensorLogger
        return TemperatureSensorLogger(self)

    def _create_config_manager(self):
        """Factory method for creating the config manager."""
        from app.backend.models.config.ConfigManager import ConfigManager
        return ConfigManager(
            control_config_path=self.control_config_path,
            graph_config_path=self.graph_config_path,
            mcu_config_path=self.mcu_config_path,
        )

    def _create_climate_chamber(self):
        """Factory method for creating the climate chamber implementation."""
        # Choose implementation based on environment
        if os.environ.get('ENVIRONMENT') == 'production':
            from app.backend.models.ClimateChamber import ClimateChamber
            return ClimateChamber()
        else:
            from app.backend.models.mock.MockClimateChamber import MockClimateChamber
            return MockClimateChamber()

    def _create_controller(self):
        """Factory method for creating the controller."""
        from app.backend.controllers.ClimateChamberController import ClimateChamberController
        return ClimateChamberController(
            self,
            self.climate_chamber,
            self.config_manager.control_config
        )