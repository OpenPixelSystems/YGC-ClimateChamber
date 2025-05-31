from app.backend.Interfaces.ICalculationService import ICalculationService
from app.backend.Interfaces.IClimateChamber import IClimateChamber
from app.backend.Interfaces.IConfigManager import IConfigManager
from app.backend.Interfaces.ISensorReader import ISensorReader
from app.backend.Implementations.PeltierModule import PeltierModule
from app.backend.Technical.Logging import LoggingMixin


# Real implementation
class ClimateChamber(IClimateChamber, LoggingMixin):
    def __init__(self, sensor_reader: ISensorReader,
                 config_manager: IConfigManager,
                 calculation_service: ICalculationService):
        LoggingMixin.__init__(self)
        self.sensor_reader = sensor_reader
        self.config_manager = config_manager
        self.calculation_service = calculation_service
        self.peltierModules = []
        self.initialize_modules()
        self.sensor_data = None
        self.stop_steering = False
        calculation_service.subscribe(self.apply_control)

    def initialize_modules(self):
        try:
            # Iterate through all Sensors in the config
            for peltier_config in self.config_manager.mcu_config.peltierModules:
                self.peltierModules.append(PeltierModule(peltier_config))
            self.print(f"[ClimateChamber] [initialize_modules] Initialized {len(self.peltierModules)} Peltier module(s) into climate chamber.")
        except Exception as e:
            self.print_error(f"[ClimateChamber] [initialize_modules] Configuration error: {str(e)}")
            raise RuntimeError(f"Configuration error: {str(e)}")

    def apply_control(self, data):
        self.print("[ClimateChamber] [apply_control]", data)
        output = data.get("pid_output", 0)

        if output > 0:
            # Positive output = need to heat
            duty_cycle = min(abs(output), 100)
            for peltier in self.peltierModules:
                actual_duty_cycle = peltier.heat(duty_cycle)
                self.print(f"[ClimateChamber] Heating with duty cycle: {actual_duty_cycle}%")

        elif output < 0:
            # Negative output = need to cool
            duty_cycle = min(abs(output), 100)
            for peltier in self.peltierModules:
                actual_duty_cycle = peltier.cool(duty_cycle)
                self.print(f"[ClimateChamber] Cooling with duty cycle: {actual_duty_cycle}%")

        else:
            # Zero output = stop
            for peltier in self.peltierModules:
                peltier.stop()
            self.print("[ClimateChamber] PID output is 0. Stopping all modules.")