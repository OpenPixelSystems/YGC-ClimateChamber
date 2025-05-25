from app.backend.Interfaces.IClimateChamberController import IClimateChamberController
from app.backend.Interfaces.IGuardingService import IGuardingService
from app.backend.Interfaces.ISensorReader import ISensorReader

class GuardingService(IGuardingService):
    def __init__(self, sensor_reader: ISensorReader, controller: IClimateChamberController):
        self.sensor_reader = sensor_reader
        self.controller = controller
        self.sensor_reader.subscribe(self.monitor_system)

    def monitor_system(self, sensor_data):
        self.monitor_temperature(sensor_data["temperature"])
        self.monitor_current(sensor_data["current"])

    def monitor_temperature(self, temperature_data):
        pass

    def monitor_current(self, current_data):
        pass

