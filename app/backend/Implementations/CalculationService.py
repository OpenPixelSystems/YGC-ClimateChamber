import collections
from datetime import datetime

from app.backend.Interfaces.ICalculationService import ICalculationService
from app.backend.Interfaces.IConfigManager import IConfigManager
from app.backend.Services.Subscribe import Subscriptable
from app.backend.Technical.Logging import LoggingMixin


class CalculationService(ICalculationService, Subscriptable, LoggingMixin):
    def __init__(self, config_manager: IConfigManager, use_adaptive_control: bool = False):
        Subscriptable.__init__(self)
        LoggingMixin.__init__(self)
        self.was_paused = None
        self.config_manager = config_manager
        self.use_adaptive_control = use_adaptive_control

        # PID controller state
        self.last_error = 0
        self.integral = 0
        self.last_time = None

        # Temperature trend tracking for adaptive control (only if needed)
        if self.use_adaptive_control:
            self.temp_history = collections.deque(maxlen=10)  # Last 10 readings
            self.time_history = collections.deque(maxlen=10)
            self.output_history = collections.deque(maxlen=5)  # Track recent outputs

    def manual_pid_control(self, power):
        self.notify({"pid_output": power, "current_temp": 0, "target_temp": 0, "error": 0})
        return power

    def _calculate_temperature_trend(self):
        """Calculate temperature rise rate and predict if we're on track."""
        if len(self.temp_history) < 3:
            return 0, False  # Not enough data

        # Calculate temperature rise rate (°C per second)
        time_span = (self.time_history[-1] - self.time_history[0]).total_seconds()
        if time_span <= 0:
            return 0, False

        temp_change = self.temp_history[-1] - self.temp_history[0]
        rise_rate = temp_change / time_span

        # Check if temperature is rising consistently
        recent_temps = list(self.temp_history)[-5:]  # Last 5 readings
        is_rising_consistently = all(recent_temps[i] >= recent_temps[i - 1] - 0.1
                                     for i in range(1, len(recent_temps)))

        return rise_rate, is_rising_consistently

    def _predict_temperature_in_time(self, current_temp, rise_rate, seconds_ahead=30):
        """Predict temperature after given time based on current trend."""
        return current_temp + (rise_rate * seconds_ahead)

    def _calculate_adaptive_output_limit(self, current_temp, target_temp, rise_rate, is_rising):
        """Calculate maximum output based on temperature trend and proximity to target."""
        temp_gap = target_temp - current_temp

        # Base output limit (percentage)
        base_limit = 100

        # If we're close to target and rising well, limit output
        if temp_gap <= 5.0 and is_rising and rise_rate > 0:
            # Predict where we'll be in 30 seconds
            predicted_temp = self._predict_temperature_in_time(current_temp, rise_rate, 30)
            overshoot_risk = predicted_temp - target_temp

            if overshoot_risk > 0:
                # High risk of overshoot - significantly limit output
                if overshoot_risk > 2.0:
                    base_limit = 20  # Very conservative
                elif overshoot_risk > 1.0:
                    base_limit = 40  # Moderate
                else:
                    base_limit = 60  # Gentle reduction

        # Further limit based on temperature gap
        if temp_gap <= 2.0:
            base_limit = min(base_limit, 30)  # Very close to target
        elif temp_gap <= 1.0:
            base_limit = min(base_limit, 15)  # Extremely close

        # If temperature is rising faster than expected, reduce output
        expected_rise_rate = temp_gap / 60  # Expect to close gap in ~1 minute
        if rise_rate > expected_rise_rate * 1.5:  # Rising 50% faster than needed
            base_limit = min(base_limit, 40)

        return base_limit

    def calculate_pid_control(self, current_temp, target_temp):
        """Apply PID control - either standard or adaptive based on initialization."""
        if self.use_adaptive_control:
            self.print("[CalculationService] [calculate_pid_control] Using adaptive pid control")
            return self._calculate_adaptive_pid_control(current_temp, target_temp)
        else:
            self.print("[CalculationService] [calculate_pid_control] Using standard pid control")
            return self._calculate_standard_pid_control(current_temp, target_temp)

    def _calculate_standard_pid_control(self, current_temp, target_temp):
        """Apply standard PID control based on current and target temperatures."""
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
            self.was_paused = False  # Track pause state
            return 0  # Output on first run

        dt = (current_time - self.last_time).total_seconds()

        # Handle resuming from pause
        if hasattr(self, 'was_paused') and self.was_paused:
            # Reset state when resuming from pause to prevent spikes
            self.integral = 0  # Clear accumulated integral
            self.last_error = error  # Reset last error to current
            self.was_paused = False  # Clear pause flag
            # Use a conservative time delta for the first calculation after pause
            dt = min(dt, 1.0)

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
            derivative = -1 * (current_temp - (target_temp - self.last_error)) / dt
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
        self.notify({"pid_output": output, "current_temp": current_temp, "target_temp": target_temp, "error": error})
        return output

    def _calculate_adaptive_pid_control(self, current_temp, target_temp):
        """Apply adaptive PID control with temperature trend analysis."""
        error = target_temp - current_temp
        current_time = datetime.now()

        # Store temperature history for trend analysis
        self.temp_history.append(current_temp)
        self.time_history.append(current_time)

        # Get PID coefficients from config
        kp = self.config_manager.control_config.kp
        ki = self.config_manager.control_config.ki
        kd = self.config_manager.control_config.kd

        if self.last_time is None:
            # First run
            self.last_time = current_time
            self.last_error = error
            self.integral = 0
            self.was_paused = False  # Track pause state
            return 0  # Output on first run

        dt = (current_time - self.last_time).total_seconds()

        # Handle resuming from pause
        if hasattr(self, 'was_paused') and self.was_paused:
            # Reset state when resuming from pause to prevent spikes
            self.integral = 0  # Clear accumulated integral
            self.last_error = error  # Reset last error to current
            self.was_paused = False  # Clear pause flag
            # Use a conservative time delta for the first calculation after pause
            dt = min(dt, 1.0)

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
            derivative = -1 * (current_temp - (target_temp - self.last_error)) / dt
        else:
            derivative = 0

        # Calculate unclamped output
        unclamped_output = p_term + ki * self.integral + kd * derivative

        # Analyze temperature trend for adaptive control
        rise_rate, is_rising = self._calculate_temperature_trend()

        # Calculate adaptive output limit
        output_limit = self._calculate_adaptive_output_limit(
            current_temp, target_temp, rise_rate, is_rising
        )

        # Apply adaptive limiting instead of fixed -100 to 100
        adaptive_max = min(100, output_limit)
        adaptive_min = max(-100, -output_limit)

        # Clamp output to adaptive limits
        output = max(adaptive_min, min(adaptive_max, unclamped_output))

        # Anti-windup: back-calculate integral when output is saturated
        if output != unclamped_output and ki != 0:
            # Adjust integral to prevent windup
            self.integral = (output - p_term - kd * derivative) / ki

        # Store output history
        self.output_history.append(output)

        # Update state for next iteration
        self.last_error = error
        self.last_time = current_time

        # Enhanced notification with trend data
        self.notify({
            "pid_output": output,
            "current_temp": current_temp,
            "target_temp": target_temp,
            "error": error,
            "rise_rate": rise_rate,
            "is_rising": is_rising,
            "output_limit": output_limit,
            "predicted_temp_30s": self._predict_temperature_in_time(current_temp, rise_rate, 30)
        })

        return output

    def pause(self, current_temp, target_temp):
        """Pause the PID controller and mark the pause state."""
        # Set the pause flag so the next calculate_pid_control call knows we were paused
        self.was_paused = True
        self.print("[CalculationService] [pause] Temperature or current threshold exceeded reached. Steering paused until values return to normal.")

        # Update the last_time to current time to prevent huge dt calculations
        self.last_time = datetime.now()

        self.notify({"pid_output": 0, "current_temp": current_temp, "target_temp": target_temp,
                     "error": target_temp - current_temp})
    def stop(self):
        """Stop the PID controller."""
        self.notify({"pid_output": 0})
