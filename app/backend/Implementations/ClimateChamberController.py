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
        self.flow_executor = None  # Will be set when flow execution starts
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
            # Collect all available viable sensor values
            available_sensor_values = []
            for sensor_name in self.viable_sensors:
                if sensor_name in data and data[sensor_name]['sensor_value'] is not None:
                    available_sensor_values.append(data[sensor_name]['sensor_value'])

            # Check for flow execution mode first
            if self.flow_executor and self.flow_executor.is_executing and available_sensor_values:
                self.handle_flow_execution(available_sensor_values)
            # Apply steering logic if we have a desired temperature profile and viable sensors
            elif self.desired_graph and available_sensor_values:
                current_temp = sum(available_sensor_values) / len(available_sensor_values)
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
            elif not available_sensor_values:
                self.print(f"[ClimateChamberController] [on_sensor_data] No steering possible due to absent viable sensor data. Available sensors: {list(data.keys())}")
            else:
                # Manual mode handling
                current_temp = sum(available_sensor_values) / len(available_sensor_values) if available_sensor_values else None

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
        """Generator function for Server-Sent Events (SSE) - streams pre-calculated data."""
        while self.running:
            try:
                # Get the latest sensor data (already processed in background)
                data = self.latest_sensor_data.copy() if self.latest_sensor_data else {}

                # Add latest control data if available
                if self.latest_control_data:
                    data['calculation_data'] = self.latest_control_data.copy()
                
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
                    current_temp = None
                    if available_sensor_values:
                        current_temp = sum(available_sensor_values) / len(available_sensor_values)

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

    def set_flow_executor(self, flow_executor):
        """Set the flow executor for flow-based control"""
        self.flow_executor = flow_executor
        self.print(f"[ClimateChamberController] Flow executor set: {flow_executor.flow_id if flow_executor else None}")

    def handle_flow_execution(self, available_sensor_values):
        """Handle sensor data during flow execution"""
        if not self.flow_executor or not self.flow_executor.is_executing:
            return

        # Calculate average temperature from inside sensors
        current_temp = sum(available_sensor_values) / len(available_sensor_values)

        # Calculate elapsed time since flow start
        elapsed_time = (datetime.now() - self.flow_executor.start_time).total_seconds()

        # Get target temperature for current step
        target_temp = self.flow_executor.get_target_temperature()
        control_action = self.flow_executor.get_control_action()

        self.print(f"[FlowExecution] Step: {control_action}, Target: {target_temp}, Current: {current_temp:.1f}°C")

        # Check if we should advance to next step
        if self.flow_executor.should_advance_step(current_temp, elapsed_time):
            if self.flow_executor.advance_to_next_step():
                self.print(f"[FlowExecution] Advanced to step {self.flow_executor.current_step_index + 1}")
                # Update target for new step
                target_temp = self.flow_executor.get_target_temperature()
                control_action = self.flow_executor.get_control_action()
            else:
                # Flow completed
                self.print(f"[FlowExecution] Flow execution completed")
                self.flow_executor.stop_execution()
                return

        # Apply control based on current step
        if control_action == 'initialize':
            # Start node - just read temperature, no control
            output = 0
            control_status = "INITIALIZING"
            self.print(f"[FlowExecution] Initializing - Current temperature: {current_temp:.1f}°C")

        elif control_action == 'complete':
            # End node or execution finished
            output = 0
            control_status = "COMPLETE"
            self.print(f"[FlowExecution] Flow execution complete")

        elif target_temp is not None:
            # Temperature control step - use calculation service or fallback PID
            if self.guarding_service.get_guarding_state():
                self.print("[FlowExecution] Pausing steering, guarding active")
                self.calculation_service.pause(current_temp, target_temp)
                output = 0
                control_status = "GUARDED"
            else:
                try:
                    # Try to use calculation service
                    output = self.calculation_service.calculate_pid_control(current_temp, target_temp, elapsed_time)
                    control_status = "FLOW_ACTIVE"
                    self.print(f"[FlowExecution] PID control: {output:.1f}% (Target: {target_temp}°C)")
                except Exception as e:
                    # Fallback to simple PID if calculation service fails
                    self.print(f"[FlowExecution] Calculation service failed, using fallback PID: {e}")
                    output = self._simple_pid_control(current_temp, target_temp)
                    control_status = "FLOW_FALLBACK"

        else:
            # No target temperature (shouldn't happen in normal flow)
            output = 0
            control_status = "NO_TARGET"

        # Apply the control output
        self.current_power = output
        self.climate_chamber.apply_control({
            'pid_output': output,
            'current_temp': current_temp,
            'target_temp': target_temp,
            'error': (target_temp - current_temp) if target_temp else None,
            'mode': 'FLOW_EXECUTION',
            'status': control_status
        })

        # Store latest control data for streaming
        self.latest_control_data = {
            'pid_output': output,
            'target_temp': target_temp,
            'control_error': (target_temp - current_temp) if target_temp else None,
            'control_status': control_status,
            'flow_step': self.flow_executor.current_step_index,
            'flow_action': control_action
        }

    def _simple_pid_control(self, current_temp, target_temp):
        """Simple PID controller fallback for flow execution"""
        if not hasattr(self, '_pid_integral'):
            self._pid_integral = 0
            self._pid_previous_error = 0

        # Simple PID constants (can be made configurable)
        kp = 10.0  # Proportional gain
        ki = 0.1   # Integral gain
        kd = 1.0   # Derivative gain

        error = target_temp - current_temp
        self._pid_integral += error
        derivative = error - self._pid_previous_error

        output = kp * error + ki * self._pid_integral + kd * derivative

        # Clamp output to reasonable range
        output = max(-100, min(100, output))

        self._pid_previous_error = error

        self.print(f"[FlowExecution] Simple PID: P={kp*error:.1f}, I={ki*self._pid_integral:.1f}, D={kd*derivative:.1f}, Output={output:.1f}")

        return output