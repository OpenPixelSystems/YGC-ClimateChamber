from pathlib import Path
import subprocess
import sys
from app.backend.Providers.gpio_provider import GPIO

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

        self.__climate_chamber_factory()

    def __climate_chamber_factory(self):
        # Create components using the factory
        """ Config manager instance """
        self.config_manager = self._create_config_manager()
        """ Reader instance used to initialise and read Sensors """
        self.sensor_reader = self._create_sensor_reader()
        """ Guarding service instance """
        self.guarding_service = self._create_guarding_service()
        """ Calculation service instance """
        self.calculation_service = self._create_calculation_service()
        """ Database instance used to log, retrieve and delete Sensors """
        self.database = self._create_database_manager()
        """ Fan controller instance to control fan speeds."""
        self.fan_controller = self._create_fan_controller()
        """ Climate chamber controller used to control Peltier elements based on sensor data and desired graph."""
        self.climate_chamber = self._create_climate_chamber()
        self.controller = self._create_controller()
        """ Reader instance used to validate temperature input """
        self.temperature_service = self._create_temperature_service()

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
        return DatabaseManager("database.db", self.sensor_reader, self.calculation_service)

    def _create_guarding_service(self):
        """Factory method for creating the temperature logger."""
        from app.backend.Services.GuardingService import GuardingService
        return GuardingService(self.sensor_reader, self.config_manager)

    def _create_calculation_service(self):
        """Factory method for creating the temperature logger."""
        from app.backend.Implementations.CalculationService import CalculationService
        return CalculationService(self.config_manager, False)

    def _create_fan_controller(self):
        from app.backend.Implementations.FanController import FanController
        return FanController(self.config_manager.mcu_config)

    def _create_climate_chamber(self):
        """Factory method for creating the climate chamber implementation."""
        from app.backend.Implementations.ClimateChamber import ClimateChamber
        return ClimateChamber(self.sensor_reader, self.config_manager, self.calculation_service, self.fan_controller)

    def _create_controller(self):
        """Factory method for creating the controller."""
        from app.backend.Implementations.ClimateChamberController import ClimateChamberController
        return ClimateChamberController(
            self.sensor_reader, self.config_manager, self.climate_chamber, self.calculation_service, self.guarding_service)

    def _create_temperature_service(self):
        """Factory method for creating the temperature logger."""
        from app.backend.Services.TemperatuurService import TemperatureService
        return TemperatureService(self.config_manager, self.controller)

    def reload_climate_chamber(self):
        """
        Reload the climate chamber components after config changes.
        
        WARNING: This method should NOT be used for raspberry_pi_config.json changes
        as it struggles with overwriting PWM configured pins. For raspberry_pi_config
        changes, use restart_climate_chamber_service() instead to fully restart the service.
        """
        print("[app_state] [reload_climate_chamber] Reloading climate chamber")
        #TODO check new config before loading in climate chamber, check should happen in config manager
        #TODO reload struggles with overwriting PWM configured pin - use restart_climate_chamber_service for GPIO changes
        GPIO.cleanup()
        self.__climate_chamber_factory()

    def restart_climate_chamber_service(self):
        """Restart the systemd service"""
        try:
            print("[app_state] [restart_climate_chamber_service] Restarting climate chamber")
            subprocess.run(['sudo', 'systemctl', 'restart', 'climatechamber.service'],
                           check=True)
            # Exit the current process cleanly
            sys.exit(0)
        except subprocess.CalledProcessError as e:
            print(f"[app_state] [restart_climate_chamber_service] Failed to restart service: {e}")
            sys.exit(1)