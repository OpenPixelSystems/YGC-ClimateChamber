import json
import time
from datetime import datetime

from app.backend.Interfaces.IGuardingService import IGuardingService
from app.backend.Technical.Logging import LoggingMixin
from app.routes.Helper.graph import Graph
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
        self.sensor_group = "Peltier"
        self.viable_sensor = "inside_on_peltier"
        self.sensor_reader = sensor_reader
        self.config_manager = config_manager
        self.climate_chamber = climate_chamber
        self.calculation_service = calculation_service
        self.guarding_service = guarding_service

        self.running = False
        self.desired_graph : Graph = None
        self.current_power = 0
        self.latest_sensor_data = {}
        self.latest_control_data = {}
        
        # Subscribe to sensor data for background steering
        self.sensor_reader.subscribe(self.on_sensor_data)

    def on_sensor_data(self, data):
        """Handle sensor data and apply steering logic in background"""
        if not self.running:
            return
            
        # Store the latest sensor data for streaming
        self.latest_sensor_data = data.copy()
        
        try:
            # Apply steering logic if we have a desired temperature profile
            if (self.desired_graph and
                    self.viable_sensor in data and
                    data[self.viable_sensor]['sensor_value'] is not None):
                current_temp = data[self.viable_sensor]['sensor_value']
                target_temp = self.desired_graph.get_temperature_at_time()
                current_time_offset = round((datetime.now() - self.desired_graph.start_time).total_seconds())
                
                if self.guarding_service.get_guarding_state():
                    self.print("[ClimateChamberController] [on_sensor_data] Pausing steering, max or min sensor temperature exceeded.")
                    self.calculation_service.pause(current_temp, target_temp)
                    output = 0
                    control_status = "GUARDED"
                else:
                    output = self.calculation_service.calculate_pid_control(current_temp, target_temp, current_time_offset)
                    self.print("[ClimateChamberController] [on_sensor_data] PID steering active")
                    control_status = "ACTIVE"

                self.current_power = output
                self.latest_control_data = {
                    'pid_output': output,
                    'target_temp': target_temp, 
                    'control_error': target_temp - current_temp,
                    'control_status': control_status
                }
            elif(self.viable_sensor not in data or
                    data[self.viable_sensor]['sensor_value'] is None):
                self.print(f"[ClimateChamberController] [on_sensor_data] No steering possible due to absent sensor data. {self.viable_sensor}")
            else:
                # Manual mode handling
                current_temp = data.get(self.viable_sensor, {}).get('sensor_value') if self.viable_sensor in data else None
                
                if self.guarding_service.get_guarding_state():
                    manual_status = "MANUAL_GUARDED"
                else:
                    manual_status = "MANUAL"
                
                self.calculation_service.manual_pid_control(self.current_power, current_temp, None)
                self.latest_control_data = {
                    'pid_output': self.current_power,
                    'Peltier power': self.current_power,
                    'control_status': manual_status
                }
                
        except Exception as e:
            self.print_error(f"[ClimateChamberController] [on_sensor_data] Error in background steering: {str(e)}")

    def set_desired_graph(self, graph):
        """Set the desired temperature profile."""
        self.print("[ClimateChamberController] [set_desired_graph] Desired flow graph set for climate chamber control")
        self.desired_graph = graph
        # Pass the schedule to the calculation service for predictive control
        self.calculation_service.set_setpoint_schedule(graph)

    def set_start_time(self, start_time):
        self.desired_graph.set_start_time(start_time)

    def get_start_time(self):
        return self.desired_graph.start_time

    def start_sensor_stream(self):
        """Start the sensor data stream."""
        self.running = True
        self.climate_chamber.start()
        self.sensor_reader.start_background_reading()  # Start background sensor reading
        self.calculation_service.last_time = datetime.now()  # Initialize timestamp
        self.print("[ClimateChamberController] [start_sensor_stream] ClimateChamberController: Sensor stream started.")

    def manual_control(self, power):
        """Manually steer peltier power"""
        if self.guarding_service.get_guarding_state():
            self.print()
            self.current_power = 0
            self.print(f"[ClimateChamberController] [manual_control] Control sensor value exceeded reset peltier power: {self.current_power}")
        else:
            self.current_power = power
            self.print(f"[ClimateChamberController] [manual_control] Manually steer peltier power {power}")

    def stop_sensor_stream(self):
        """Stop the sensor data stream."""
        self.running = False
        self.current_power = 0
        self.calculation_service.stop()
        self.climate_chamber.stop()
        self.sensor_reader.stop_background_reading()  # Stop background sensor reading
        self.disable_peltier_driver()
        self.print("[ClimateChamberController] [stop_sensor_stream] Sensor stream stopped.")

    def sensor_data_provider(self):
        """Generator function for Server-Sent Events (SSE) - streams pre-calculated data."""
        while self.running:
            try:
                # Get the latest sensor data (already processed in background)
                data = self.latest_sensor_data.copy() if self.latest_sensor_data else {}
                
                # Add latest control data if available
                if self.latest_control_data:
                    data['calculation_data'] = self.latest_control_data.copy()
                
                # Add guarding information to the data stream
                data['guarding_info'] = self.guarding_service.get_guarding_info()
                
                self.print_debug(f"[ClimateChamberController] [sensor_data_provider] Streaming data to webpage {data}")
                yield f"data: {json.dumps(data)}\n\n"
                
            except Exception as e:
                yield f"data: {{\"error\": \"Failed to stream sensor data: {str(e)}\"}}\n\n"

            time.sleep(self.config_manager.control_config.read_delay)

        yield "data: {\"status\": \"stopped\"}\n\n"

    def enable_peltier_driver(self):
        self.print(f"[ClimateChamberController] [enable_peltier_driver] Enabled Peltier driver. ")
        self.climate_chamber.enable_peltier_modules()

    def disable_peltier_driver(self):
        self.print(f"[ClimateChamberController] [disable_peltier_driver] Disabled Peltier driver. ")
        self.climate_chamber.disable_peltier_modules()