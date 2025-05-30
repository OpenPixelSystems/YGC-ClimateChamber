import json
import time
from datetime import datetime

from app.backend.Interfaces.IGuardingService import IGuardingService
from app.backend.Technical.Logging import LoggingMixin
from app.backend.graph import Graph
from app.backend.Implementations.CalculationService import CalculationService
from app.backend.Interfaces.IClimateChamber import IClimateChamber
from app.backend.Interfaces.IClimateChamberController import IClimateChamberController
from app.backend.Interfaces.IConfigManager import IConfigManager
from app.backend.Interfaces.ISensorReader import ISensorReader


class ClimateChamberController(IClimateChamberController, LoggingMixin):
    """
    Handles the control logic of the climate chamber separately from hardware management.
    Entry point into backend application controlling the climate chamber
    """

    def __init__(self, sensor_reader: ISensorReader, config_manager: IConfigManager, climate_chamber: IClimateChamber,
                 calculation_service: CalculationService, guarding_service: IGuardingService):
        """Initialize the controller with the climate chamber instance and config."""
        super().__init__()
        self.sensor_reader = sensor_reader
        self.config_manager = config_manager
        self.climate_chamber = climate_chamber
        self.calculation_service = calculation_service
        self.guarding_service = guarding_service

        self.running = False
        self.desired_graph : Graph = None
        self.current_power = 0

    def set_desired_graph(self, graph):
        """Set the desired temperature profile."""
        self.print("Desired flow graph set for climate chamber control")
        self.desired_graph = graph

    def set_start_time(self, start_time):
        self.desired_graph.set_start_time(start_time)

    def get_start_time(self):
        return self.desired_graph.start_time

    def start_sensor_stream(self):
        """Start the sensor data stream."""
        self.running = True
        self.calculation_service.last_time = datetime.now()  # Initialize timestamp
        self.print("\nClimateChamberController: Sensor stream started.")

    def manual_control(self, power):
        """Manually steer peltier power"""
        if self.guarding_service.get_guarding_state():
            self.print()
            self.current_power = self.calculation_service.manual_pid_control(0)
            self.print(f"\n[ClimateChamberController] [manual_control] Control sensor value exceeded reset peltier power: {self.current_power}")
        else:
            self.current_power = self.calculation_service.manual_pid_control(power)
            self.print(f"\n[ClimateChamberController] [manual_control] Manually steer peltier power {power}")

    def stop_sensor_stream(self):
        """Stop the sensor data stream."""
        self.running = False
        self.current_power = 0
        self.calculation_service.stop()
        self.print("\n[ClimateChamberController] [stop_sensor_stream] Sensor stream stopped.")

    def sensor_data_provider(self):
        """Generator function for Server-Sent Events (SSE)."""
        while self.running:
            try:
                data = self.sensor_reader.read_sensors()

                # If we have a desired temperature profile, apply control
                if self.desired_graph and data['DS18B20']: #TODO currently only uses one sensor, extend to average of applicable sensors
                    current_temp = data['DS18B20']['Inside_on_device']
                    target_temp = self.desired_graph.get_temperature_at_time()
                    self.print("Target temperature is: ", target_temp)
                    if self.guarding_service.get_guarding_state():
                        self.calculation_service.pause(current_temp, target_temp)
                        output = 0
                    else:
                        output = self.calculation_service.calculate_pid_control(current_temp, target_temp)
                        self.print("PID steering active")

                    self.current_power = output
                    # Add control info to the data
                    data['calculation_data'] = {'pid_output':output,'target_temp': target_temp, 'control_error': target_temp - current_temp}
                else:
                    data['calculation_data'] = {'Peltier power':self.current_power}
                self.print(f"Sending data to webpage {data}")
                yield f"data: {json.dumps(data)}\n\n"
            except (FileNotFoundError, json.JSONDecodeError) as e:
                yield f"data: {{\"error\": \"Failed to read sensor data: {str(e)}\"}}\n\n"

            time.sleep(self.config_manager.control_config.read_delay)

        self.desired_graph = None
        yield "data: {\"status\": \"stopped\"}\n\n"