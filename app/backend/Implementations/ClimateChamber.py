from app.backend.Interfaces.IClimateChamber import IClimateChamber
from app.backend.Interfaces.IConfigManager import IConfigManager
from app.backend.Interfaces.ISensorReader import ISensorReader
from app.backend.Implementations.PeltierModule import PeltierModule


# Real implementation
class ClimateChamber(IClimateChamber):
    #TODO implement Peltier control logic
    def __init__(self, sensor_reader: ISensorReader, config_manager: IConfigManager):
        self.sensor_reader = sensor_reader
        self.config_manager = config_manager

        self.peltierModules = []
        self.initialize_modules()

    def initialize_modules(self):
        try:
            # Iterate through all Sensors in the config
            for peltier_config in self.config_manager.mcu_config.peltierModules:
                self.peltierModules.append(PeltierModule(peltier_config))
            print(f"[ClimateChamber] [initialize_modules] Initialized {len(self.peltierModules)} Peltier module(s) into climate chamber.")
        except Exception as e:
            raise RuntimeError(f"Configuration error: {str(e)}")

    def set_heating(self, power: float):
        pass

    def set_cooling(self, power: float):
        pass

    def stop_all(self):
        pass

    def cleanup(self):
        return



