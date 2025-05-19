from pathlib import Path

from app.backend.temperature import TemperatureService

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
        # Shared storage between models, controllers and Services
        self.desired_flow_graph = None
        self.start_time = None

        # Paths
        self.config_dir = Path('app/backend/config')
        self.graph_config_path = self.config_dir / 'graph_config.json'
        self.control_config_path = self.config_dir / 'control_config.json'
        self.mcu_config_path = self.config_dir / 'raspberry_pi_config.json'

        # Create components using the factory
        """ Config manager instance """
        self.config_manager = self._create_config_manager()
        """ Reader instance used to initialise and read Sensors """
        self.sensor_reader = self._create_sensor_reader()
        """ Database instance used to log, retrieve and delete Sensors """
        self.database = self._create_database_manager()
        """ Calculation service instance """
        self.calculation_service = self._create_calculation_service()
        """ Climate chamber controller used to control Peltier elements based on sensor data and desired graph."""
        self.climate_chamber = self._create_climate_chamber()
        self.controller = self._create_controller()
        """ Reader instance used to validate temperature input """
        self.temperature_service = TemperatureService(self.config_manager, self.controller)

    def _create_config_manager(self):
        """Factory method for creating the config manager."""
        from app.backend.Implementations.ConfigManager import ConfigManager
        return ConfigManager(
            control_config_path=self.control_config_path,
            graph_config_path=self.graph_config_path,
            mcu_config_path=self.mcu_config_path,
        )

    def _create_sensor_reader(self):
        """Factory method for creating the sensor reader."""
        from app.backend.Implementations.SensorReader import SensorReader
        return SensorReader(self.config_manager.mcu_config)

    def _create_database_manager(self):
        """Factory method for creating the temperature logger."""
        from app.backend.Implementations.DatabaseManager import DatabaseManager
        return DatabaseManager("database.db", self.sensor_reader)

    def _create_calculation_service(self):
        """Factory method for creating the temperature logger."""
        from app.backend.Implementations.CalculationService import CalculationService
        return CalculationService(self.config_manager)

    def _create_climate_chamber(self):
        """Factory method for creating the climate chamber implementation."""
        # Choose implementation based on environment
        from app.backend.Implementations.ClimateChamber import ClimateChamber
        return ClimateChamber(self.sensor_reader, self.config_manager)

    def _create_controller(self):
        """Factory method for creating the controller."""
        from app.backend.Implementations.ClimateChamberController import ClimateChamberController
        return ClimateChamberController(
            self.sensor_reader, self.config_manager, self.climate_chamber, self.calculation_service
        )