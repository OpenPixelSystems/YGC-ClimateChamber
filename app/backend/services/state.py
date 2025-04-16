from threading import Lock
from pathlib import Path
import os

class AppState:
    """Global singleton for project-wide state management."""
    _instance = None
    _lock = Lock()

    def __new__(cls):
        """Ensures only one instance of AppState is created."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(AppState, cls).__new__(cls)
                    cls._instance._init_state()
        return cls._instance

    def _init_state(self):
        """Initializes instance variables (only runs once)."""
        self.desired_flow_graph = None
        self.start_time = None
        self.read_interval = 0.1
        self.provider_interval = 1
        # Paths
        self.config_dir = Path('app/backend/config')
        self.graph_config_path = self.config_dir / 'graph_config.json'
        self.control_config_path = self.config_dir / 'control_config.json'
        self.sensor_data_path = self.config_dir / 'sensor_data.json'

        # Ensure config directory exists
        os.makedirs(self.config_dir, exist_ok=True)

        # Create components using the factory
        """ Database instance used to log, retrieve and delete sensors """
        self.database = self._create_temperature_logger()
        """ Config manager instance """
        self.config_manager = self._create_config_manager()
        """ Climate chamber controller used to control Peltier elements based on sensor data and desired graph."""
        self.climate_chamber = self._create_climate_chamber()
        self.controller = self._create_controller()

    def _create_temperature_logger(self):
        """Factory method for creating the config manager."""
        from database.TemperatureSensorLogger import TemperatureSensorLogger
        return TemperatureSensorLogger(self)

    def _create_config_manager(self):
        """Factory method for creating the config manager."""
        from app.backend.models.config.ConfigManager import ConfigManager
        return ConfigManager(str(self.control_config_path))

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
            self.config_manager.pid_config
        )