import json
import time
from datetime import datetime

from app.backend.graph import Graph
from app.backend.Implementations.CalculationService import CalculationService
from app.backend.Interfaces.IClimateChamber import IClimateChamber
from app.backend.Interfaces.IClimateChamberController import IClimateChamberController
from app.backend.Interfaces.IConfigManager import IConfigManager
from app.backend.Interfaces.ISensorReader import ISensorReader


class ClimateChamberController(IClimateChamberController):
    """
    Handles the control logic of the climate chamber separately from hardware management.
    Entry point into backend application controlling the climate chamber
    """

    def __init__(self, sensor_reader: ISensorReader, config_manager: IConfigManager, climate_chamber: IClimateChamber, calculation_service : CalculationService):
        """Initialize the controller with the climate chamber instance and config."""
        self.sensor_reader = sensor_reader
        self.config_manager = config_manager
        self.climate_chamber = climate_chamber
        self.calculation_service =  calculation_service

        self.running = False
        self.desired_graph : Graph = None

    def set_desired_graph(self, graph):
        """Set the desired temperature profile."""
        print("Desired flow graph set for climate chamber control")
        self.desired_graph = graph

    def set_start_time(self, start_time):
        self.desired_graph.set_start_time(start_time)

    def get_start_time(self):
        return self.desired_graph.start_time

    def start_sensor_stream(self):
        """Start the sensor data stream."""
        self.running = True
        self.calculation_service.last_time = datetime.now()  # Initialize timestamp
        print("\nClimateChamberController: Sensor stream started.")

    def stop_sensor_stream(self):
        """Stop the sensor data stream."""
        self.running = False
        print("\nClimateChamberController: Sensor stream stopped.")
        self.climate_chamber.stop_all()  # Ensure all actuators are off

    def sensor_data_provider(self):
        """Generator function for Server-Sent Events (SSE)."""
        while self.running:
            try:
                data = self.sensor_reader.read_sensors()

                # If we have a desired temperature profile, apply control
                if self.desired_graph and data['Inside_on_device']: #TODO currently only uses one sensor, extend to average of applicable sensors
                    current_temp = data['Inside_on_device']
                    target_temp = self.desired_graph.get_temperature_at_time()
                    print("Target temperature is: ", target_temp)
                    output = self.calculation_service.calculate_pid_control(current_temp, target_temp)

                    # Add control info to the data
                    data['target_temperature'] = target_temp
                    data['pid_output'] = output
                    data['control_error'] = target_temp - current_temp
                    print("PID steering active")
                print(f"Sending data to webpage {data}")
                yield f"data: {json.dumps(data)}\n\n"
            except (FileNotFoundError, json.JSONDecodeError) as e:
                yield f"data: {{\"error\": \"Failed to read sensor data: {str(e)}\"}}\n\n"

            time.sleep(self.config_manager.control_config.read_delay)

        yield "data: {\"status\": \"stopped\"}\n\n"  # Send final message before stopping