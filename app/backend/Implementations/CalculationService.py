from datetime import datetime

from app.backend.Interfaces.ICalculationService import ICalculationService
from app.backend.Interfaces.IConfigManager import IConfigManager
from app.backend.Services.Subscribe import Subscriptable


class CalculationService(ICalculationService, Subscriptable):
    def __init__(self, config_manager: IConfigManager):
        super().__init__()
        self.config_manager = config_manager

        # PID controller state
        self.last_error = 0
        self.integral = 0
        self.last_time = None

    def manual_pid_control(self, power):
        self.notify({"pid_output": power, "current_temp": 0, "target_temp": 0, "error": 0})
        return power

    def calculate_pid_control(self, current_temp, target_temp):
        """Apply PID control based on current and target temperatures."""
        error = target_temp - current_temp

        # Get PID coefficients from config
        kp = self.config_manager.control_config.kp
        ki = self.config_manager.control_config.ki
        kd = self.config_manager.control_config.kd

        # Calculate time delta for integral and derivative terms
        current_time = datetime.now()
        if self.last_time is None:
            # First run
            self.last_time = current_time
            self.last_error = error
            self.integral = 0
            return 0  # Output on first run

        dt = (current_time - self.last_time).total_seconds()

        # Validate time delta to avoid division by very small numbers
        # and to handle long pauses between calculations
        if dt < 0.001:
            dt = 0.001  # Minimum time delta
        elif dt > 10.0:
            # If too much time has passed, reset integration
            self.integral = 0
            dt = 1.0

        # Calculate proportional term
        p_term = kp * error

        # Calculate integral term
        self.integral += error * dt

        # Calculate derivative term (on measurement, not error)
        if dt > 0:
            derivative = -1 * (current_temp - (target_temp - self.last_error)) / dt  # Derivative on measurement
        else:
            derivative = 0

        # Calculate unclamped output
        unclamped_output = p_term + ki * self.integral + kd * derivative

        # Clamp output to -100 to 100
        output = max(-100, min(100, unclamped_output))

        # Anti-windup: back-calculate integral when output is saturated
        if output != unclamped_output and ki != 0:
            # Adjust integral to prevent windup
            self.integral = (output - p_term - kd * derivative) / ki

        # Update state for next iteration
        self.last_error = error
        self.last_time = current_time
        self.notify({"pid_output": output, "current_temp":current_temp, "target_temp":target_temp, "error": error})
        return output
