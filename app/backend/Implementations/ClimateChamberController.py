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
        self.viable_sensors = []
        self.sensor_reader = sensor_reader
        self.config_manager = config_manager
        self.climate_chamber = climate_chamber
        self.calculation_service = calculation_service
        self.guarding_service = guarding_service

        self.running = False
        self.desired_graph : Graph = None
        self.current_power = 0

        self.get_inside_sensors()

    def get_inside_sensors(self):
        for sensor in self.config_manager.mcu_config.sensors:
            if sensor.type == 'NTC' and sensor.sensor_location == "Inside":
                self.viable_sensors.append(sensor.name)

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
        """Generator function for Server-Sent Events (SSE)."""
        while self.running:
            try:
                data = self.sensor_reader.read_sensors()

                # Collect all available viable sensor values
                available_sensor_values = []
                for sensor_name in self.viable_sensors:
                    if sensor_name in data and data[sensor_name]['sensor_value'] is not None:
                        available_sensor_values.append(data[sensor_name]['sensor_value'])

                # If we have a desired temperature profile and any viable sensors, apply control
                if self.desired_graph and available_sensor_values:
                    current_temp = sum(available_sensor_values) / len(available_sensor_values)
                    target_temp = self.desired_graph.get_temperature_at_time()
                    # Get current time offset for predictive control
                    current_time_offset = round((datetime.now() - self.desired_graph.start_time).total_seconds())
                    self.print("Target temperature is: ", target_temp)
                    if self.guarding_service.get_guarding_state():
                        print("[ClimateChamberController] [sensor_data_provider] Pausing steering, max or min sensor temperature exceeded.")
                        self.calculation_service.pause(current_temp, target_temp)
                        output = 0  # Force output to 0 when guarding is active
                        control_status = "GUARDED"
                    else:
                        output = self.calculation_service.calculate_pid_control(current_temp, target_temp, current_time_offset)
                        self.print("[ClimateChamberController] [sensor_data_provider] PID steering active")
                        control_status = "ACTIVE"

                    self.current_power = output
                    # Add control info to the data - ensure it reflects actual output being used
                    data['calculation_data'] = {
                        'pid_output': output,  # This will be 0 when guarded
                        'target_temp': target_temp,
                        'control_error': target_temp - current_temp,
                        'control_status': control_status
                    }
                elif not available_sensor_values:
                    print(f"[ClimateChamberController] [sensor_data_provider] No steering possible due to absent viable sensor data. Available sensors: {list(data.keys())}")

                else:
                    print(f"[ClimateChamberController] [sensor_data_provider] steering manual control {self.current_power}")
                    self.calculation_service.manual_pid_control(self.current_power)
                    data['calculation_data'] = {'Peltier power':self.current_power}
                    # In manual mode, still pass temperature data if available for logging
                    current_temp = data.get(self.viable_sensor, {}).get('sensor_value') if self.viable_sensor in data else None

                    # Check if manual power is being overridden by guarding
                    if self.guarding_service.get_guarding_state():
                        manual_status = "MANUAL_GUARDED"
                    else:
                        manual_status = "MANUAL"

                    self.calculation_service.manual_pid_control(self.current_power, current_temp, None)
                    data['calculation_data'] = {
                        'pid_output': self.current_power,  # Will be 0 if guarded
                        'Peltier power': self.current_power,  # Keep for backward compatibility
                        'control_status': manual_status
                    }

                # Add guarding information to the data stream
                data['guarding_info'] = self.guarding_service.get_guarding_info()
                
                self.print_debug(f"[ClimateChamberController] [sensor_data_provider] Sending data to webpage {data}")
                yield f"data: {json.dumps(data)}\n\n"
            except (FileNotFoundError, json.JSONDecodeError) as e:
                yield f"data: {{\"error\": \"Failed to read sensor data: {str(e)}\"}}\n\n"

            time.sleep(self.config_manager.control_config.read_delay)

        self.desired_graph = None
        yield "data: {\"status\": \"stopped\"}\n\n"

    def enable_peltier_driver(self):
        self.print(f"[ClimateChamberController] [enable_peltier_driver] Enabled Peltier driver. ")
        self.climate_chamber.enable_peltier_modules()

    def disable_peltier_driver(self):
        self.print(f"[ClimateChamberController] [disable_peltier_driver] Disabled Peltier driver. ")
        self.climate_chamber.disable_peltier_modules()