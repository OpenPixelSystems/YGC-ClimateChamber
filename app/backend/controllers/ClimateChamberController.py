import json
import time
from datetime import datetime
import asyncio


class ClimateChamberController:
    """Handles the control logic of the climate chamber separately from hardware management."""

    def __init__(self, app_state, climate_chamber, config):
        """Initialize the controller with the climate chamber instance and config."""
        self.app_state = app_state
        self.chamber = climate_chamber
        self.config = config
        self.running = False
        self.desired_graph = None

        # PID controller state
        self.last_error = 0
        self.integral = 0
        self.last_time = None

    def set_desired_graph(self, graph):
        """Set the desired temperature profile."""
        print("Desired flow graph set for climate chamber control")
        self.desired_graph = graph

    def apply_control(self, current_temp, target_temp):
        """Apply PID control based on current and target temperatures."""
        error = target_temp - current_temp

        # Get PID coefficients from config
        kp = self.config.kp
        ki = self.config.ki
        kd = self.config.kd

        # Calculate time delta for integral and derivative terms
        current_time = datetime.now()
        if self.last_time is None:
            dt = 1.0  # Default to 1 second on first run
        else:
            dt = (current_time - self.last_time).total_seconds()

        # Update integral term (with anti-windup)
        self.integral += error * dt
        self.integral = max(-100, min(100, self.integral))  # Prevent integral windup

        # Calculate derivative term
        if dt > 0:
            derivative = (error - self.last_error) / dt
        else:
            derivative = 0

        # Calculate PID output
        output = kp * error + ki * self.integral + kd * derivative

        # Apply control based on whether we need heating or cooling
        if output > 0:
            # Need heating
            self.chamber.set_heating(abs(output))
            self.chamber.set_cooling(0)
        else:
            # Need cooling
            self.chamber.set_heating(0)
            self.chamber.set_cooling(abs(output))

        # Update state for next iteration
        self.last_error = error
        self.last_time = current_time

        return output

    def start_sensor_stream(self):
        """Start the sensor data stream."""
        self.running = True
        self.last_time = datetime.now()  # Initialize timestamp
        print("\nClimateChamberController: Sensor stream started.")

    def stop_sensor_stream(self):
        """Stop the sensor data stream."""
        self.running = False
        print("\nClimateChamberController: Sensor stream stopped.")
        self.chamber.stop_all()  # Ensure all actuators are off

    def sensor_data_provider(self):
        """Generator function for Server-Sent Events (SSE)."""
        #TODO
        # Generator is currently called by stream to supply it with sensor values.
        # The stream object should rather start an separate task that starts the regulation process based on the provided desired graph (in app_state)

        while self.running:
            try:
                data = self.app_state.database.read_sensors()

                #with open(self.app_state.sensor_data_path, 'r') as file:
                #    data = json.load(file)

                # If we have a desired temperature profile, apply control
                if self.desired_graph and 'temperature' in data:
                    current_temp = data['ClimateChamber temperature']
                    target_temp = self.desired_graph.get_current_target()
                    self.apply_control(current_temp, target_temp)

                    # Add control info to the data
                    data['target_temperature'] = target_temp
                    data['control_error'] = target_temp - current_temp
                    print("PID steering active")
                print(f"Sending data to webpage {data}")
                yield f"data: {json.dumps(data)}\n\n"
            except (FileNotFoundError, json.JSONDecodeError) as e:
                yield f"data: {{\"error\": \"Failed to read sensor data: {str(e)}\"}}\n\n"

            time.sleep(self.app_state.provider_interval)

        yield "data: {\"status\": \"stopped\"}\n\n"  # Send final message before stopping