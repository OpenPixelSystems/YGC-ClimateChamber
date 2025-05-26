from app.backend.Interfaces.ICalculationService import ICalculationService
from app.backend.Interfaces.IClimateChamber import IClimateChamber
from app.backend.Interfaces.IConfigManager import IConfigManager
from app.backend.Interfaces.ISensorReader import ISensorReader
from app.backend.Implementations.PeltierModule import PeltierModule


# Real implementation
class ClimateChamber(IClimateChamber):
    def __init__(self, sensor_reader: ISensorReader, config_manager: IConfigManager, calculation_service: ICalculationService):
        self.sensor_reader = sensor_reader
        self.config_manager = config_manager
        self.calculation_service = calculation_service
        self.critical_sensors = []
        self.get_critical_sensors()
        self.peltierModules = []
        self.initialize_modules()
        self.sensor_data = None
        calculation_service.subscribe(self.apply_control)
        sensor_reader.subscribe(self.save_sensor_limits)

    def initialize_modules(self):
        try:
            # Iterate through all Sensors in the config
            for peltier_config in self.config_manager.mcu_config.peltierModules:
                self.peltierModules.append(PeltierModule(peltier_config))
            print(f"[ClimateChamber] [initialize_modules] Initialized {len(self.peltierModules)} Peltier module(s) into climate chamber.")
        except Exception as e:
            raise RuntimeError(f"Configuration error: {str(e)}")

    def apply_control(self, data):
        print("[ClimateChamber] [apply_control]", data)

        output = data.get("pid_output", 0)

        if output > 0:
            # Positive output = need to heat
            duty_cycle = min(abs(output), 100)
            for peltier in self.peltierModules:
                peltier.heat(duty_cycle)
            print(f"[ClimateChamber] Heating with duty cycle: {duty_cycle}%")

        elif output < 0:
            # Negative output = need to cool
            duty_cycle = min(abs(output), 100)
            for peltier in self.peltierModules:
                peltier.cool(duty_cycle)
            print(f"[ClimateChamber] Cooling with duty cycle: {duty_cycle}%")

        else:
            # Zero output = stop
            for peltier in self.peltierModules:
                peltier.stop()
            print("[ClimateChamber] PID output is 0. Stopping all modules.")

    def save_sensor_limits(self, data):
        print("[ClimateChamber] [save_sensor_limits]", data)
        #TODO Check if sensor is safety_critical and store result
        temperature_readings = data['DS18B20']
        current_readings = data['ADS1115']

        for sensor_name, temperature in temperature_readings.items():
            for sensor in self.critical_sensors:
                if sensor.name == sensor_name:
                    if temperature > sensor.max_value:
                        print(f'[ClimateChamber][save_sensor_limits] value for sensor {sensor_name} above threshold limits')

    def get_critical_sensors(self):
        for sensor in self.config_manager.mcu_config.sensors:
            if sensor.critical:
                self.critical_sensors.append(sensor)
