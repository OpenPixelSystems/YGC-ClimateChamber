import collections
import math
from datetime import datetime

from app.backend.Interfaces.ICalculationService import ICalculationService
from app.backend.Interfaces.IConfigManager import IConfigManager
from app.backend.Services.Subscribe import Subscriptable
from app.backend.Technical.Logging import LoggingMixin


class CalculationService(ICalculationService, Subscriptable, LoggingMixin):
    """HVAC-optimized PID controller with deadband, anti-windup, and equipment protection."""
    
    def __init__(self, config_manager: IConfigManager, use_adaptive_control: bool = False):
        Subscriptable.__init__(self)
        LoggingMixin.__init__(self)
        self.config_manager = config_manager
        
        # Controller state
        self.was_paused = False
        self.last_error = 0
        self.integral = 0
        self.last_time = None
        self.last_pv = None  # Last process variable (temperature) for derivative calculation
        
        # HVAC specific parameters
        self.deadband = 0.5  # ±0.5°C deadband to prevent hunting
        self.max_output_rate = 25.0  # Maximum output change rate per second (%)
        self.min_on_time = 2.0  # Minimum on time for equipment protection (seconds)
        self.min_off_time = 2.0  # Minimum off time for equipment protection (seconds)
        
        # Output state tracking
        self.current_output = 0.0
        self.last_output = 0.0
        self.last_significant_output_time = None
        
        # Temperature filtering for stability
        self.temp_filter = collections.deque(maxlen=3)  # 3-point moving average
        self.setpoint_filter = collections.deque(maxlen=5)  # Setpoint ramping
        
        # Anti-windup and bumpless transfer
        self.output_limits = (-100.0, 100.0)  # Heating/Cooling limits
        self.integral_limits = (-50.0, 50.0)  # Integral windup limits
        
        # Predictive control (optional)
        self.setpoint_schedule = None
        self.feedforward_gain = 0.2  # Conservative for HVAC
        self.prediction_horizon = 60

    # =============================================================================
    # PUBLIC INTERFACE METHODS
    # =============================================================================
    
    def manual_pid_control(self, power, current_temp=None, target_temp=None):
        """Manual control mode with optional temperature logging."""
        error = (target_temp - current_temp) if (current_temp is not None and target_temp is not None) else None
        self.notify({
            "pid_output": power, 
            "current_temp": current_temp, 
            "target_temp": target_temp, 
            "error": error,
            "mode": "MANUAL",
            "status": "MANUAL_CONTROL"
        })
        return power

    def calculate_pid_control(self, current_temp, target_temp, current_time_offset=None):
        """HVAC-optimized PID control with deadband, anti-windup, and equipment protection."""
        self.print("[CalculationService] [calculate_pid_control] Using HVAC-optimized PID control")
        return self._calculate_hvac_pid_control(current_temp, target_temp, current_time_offset)

    def set_setpoint_schedule(self, schedule):
        """Set the temperature schedule for predictive control."""
        self.setpoint_schedule = schedule

    def pause(self, current_temp, target_temp):
        """Pause the HVAC PID controller for safety reasons."""
        self.was_paused = True
        self.print("[HVAC_PID] Controller paused - safety threshold exceeded")
        
        # Update timestamp to prevent large dt on resume
        self.last_time = datetime.now()
        
        # Maintain current output for bumpless transfer (don't reset to 0)
        error = target_temp - current_temp if current_temp and target_temp else 0
        
        self.notify({
            "pid_output": self.current_output,
            "current_temp": current_temp,
            "target_temp": target_temp,
            "error": error,
            "mode": "PAUSED",
            "status": "SAFETY_PAUSE"
        })
        
    def stop(self):
        """Stop the HVAC PID controller completely."""
        self.print("[HVAC_PID] Controller stopped")
        self.current_output = 0
        self.integral = 0
        self.last_time = None
        self.last_pv = None
        
        # Clear filters
        self.temp_filter.clear()
        self.setpoint_filter.clear()
        
        self.notify({
            "pid_output": 0,
            "mode": "OFF",
            "status": "STOPPED"
        })

    def subscribe(self, callback):
        """Subscribe to PID output notifications."""
        Subscriptable.subscribe(self, callback)

    # =============================================================================
    # HVAC PID CONTROL IMPLEMENTATION
    # =============================================================================

    def _calculate_hvac_pid_control(self, current_temp, target_temp, current_time_offset=None):
        """HVAC-optimized PID control with proper heating/cooling logic."""
        current_time = datetime.now()
        
        # Filter input temperature for stability
        self.temp_filter.append(current_temp)
        filtered_temp = sum(self.temp_filter) / len(self.temp_filter)
        
        # Filter setpoint for smooth changes
        self.setpoint_filter.append(target_temp)
        filtered_setpoint = sum(self.setpoint_filter) / len(self.setpoint_filter)
        
        # Calculate error
        error = filtered_setpoint - filtered_temp
        
        # Apply deadband to prevent hunting
        if abs(error) <= self.deadband:
            self.print(f"[HVAC_PID] Within deadband: error={error:.2f}°C, maintaining output={self.current_output:.1f}%")
            self._log_pid_data(filtered_temp, filtered_setpoint, error, self.current_output, "DEADBAND")
            return self.current_output
        
        # Initialize on first run
        if self.last_time is None:
            self.last_time = current_time
            self.last_error = error
            self.last_pv = filtered_temp
            self.integral = 0
            self.was_paused = False
            self.print("[HVAC_PID] First run initialization")
            return 0.0
        
        # Calculate time delta
        dt = (current_time - self.last_time).total_seconds()
        if dt <= 0:
            return self.current_output
            
        # Handle pause/resume
        if self.was_paused:
            self._reset_controller_state(error, filtered_temp)
            dt = min(dt, 1.0)
        
        # Validate time delta
        if dt > 10.0:
            self.print("[HVAC_PID] Large time gap detected, resetting integral")
            self.integral = 0
            dt = 1.0
        
        # Get PID parameters
        kp = self.config_manager.control_config.kp
        ki = self.config_manager.control_config.ki
        kd = self.config_manager.control_config.kd
        
        # Calculate PID terms
        proportional = kp * error
        
        # Integral term with anti-windup
        if not self._is_output_saturated():
            self.integral += error * dt
            # Clamp integral to prevent windup
            self.integral = max(self.integral_limits[0], min(self.integral_limits[1], self.integral))
        
        integral_term = ki * self.integral
        
        # Derivative on process variable (not error) to avoid setpoint kicks
        if self.last_pv is not None and dt > 0:
            pv_derivative = -(filtered_temp - self.last_pv) / dt
            derivative_term = kd * pv_derivative
        else:
            derivative_term = 0
        
        # Calculate raw PID output
        raw_output = proportional + integral_term + derivative_term
        
        # Add feed-forward if schedule available
        feedforward = 0
        if self.setpoint_schedule and current_time_offset is not None:
            feedforward = self._calculate_conservative_feedforward(filtered_temp, filtered_setpoint, current_time_offset)
            raw_output += feedforward
        
        # Apply output limits
        limited_output = max(self.output_limits[0], min(self.output_limits[1], raw_output))
        
        # Apply rate limiting for equipment protection
        rate_limited_output = self._apply_output_rate_limiting(limited_output, dt)
        
        # Apply minimum on/off times for equipment protection
        final_output = self._apply_minimum_times(rate_limited_output, dt)
        
        # Update state
        self.last_error = error
        self.last_pv = filtered_temp
        self.last_time = current_time
        self.last_output = self.current_output
        self.current_output = final_output
        
        # Log detailed information
        self._log_pid_data(filtered_temp, filtered_setpoint, error, final_output, "ACTIVE", {
            'proportional': proportional,
            'integral': integral_term,
            'derivative': derivative_term,
            'feedforward': feedforward,
            'raw_output': raw_output,
            'rate_limited': rate_limited_output
        })
        
        return final_output

    # =============================================================================
    # CONTROLLER PROTECTION AND LIMITING METHODS
    # =============================================================================
    
    def _reset_controller_state(self, error, temp):
        """Reset controller state after pause for bumpless transfer."""
        self.print("[HVAC_PID] Resetting controller state after pause")
        self.integral = 0  # Clear integral to prevent windup
        self.last_error = error
        self.last_pv = temp
        self.was_paused = False
    
    def _is_output_saturated(self):
        """Check if output is at limits to prevent integral windup."""
        return (self.current_output <= self.output_limits[0] + 1.0 or 
                self.current_output >= self.output_limits[1] - 1.0)
    
    def _apply_output_rate_limiting(self, desired_output, dt):
        """Apply maximum rate of change limiting for equipment protection."""
        max_change = self.max_output_rate * dt
        output_change = desired_output - self.current_output
        
        if abs(output_change) > max_change:
            if output_change > 0:
                return self.current_output + max_change
            else:
                return self.current_output - max_change
        
        return desired_output
    
    def _apply_minimum_times(self, desired_output, dt):
        """Apply minimum on/off times for equipment protection."""
        current_time = datetime.now()
        
        # Determine if we're switching between heating/cooling/off
        is_heating = desired_output > 5.0  # >5% considered heating
        is_cooling = desired_output < -5.0  # <-5% considered cooling
        is_off = abs(desired_output) <= 5.0  # ±5% considered off
        
        was_heating = self.current_output > 5.0
        was_cooling = self.current_output < -5.0
        was_off = abs(self.current_output) <= 5.0
        
        # Check if we're trying to change modes too quickly
        if self.last_significant_output_time:
            time_since_change = (current_time - self.last_significant_output_time).total_seconds()
            
            # If heating was on and we want to turn off/cool
            if was_heating and (is_off or is_cooling):
                if time_since_change < self.min_on_time:
                    self.print(f"[HVAC_PID] Minimum heating time not met ({time_since_change:.1f}s < {self.min_on_time}s)")
                    return self.current_output
            
            # If cooling was on and we want to turn off/heat  
            elif was_cooling and (is_off or is_heating):
                if time_since_change < self.min_on_time:
                    self.print(f"[HVAC_PID] Minimum cooling time not met ({time_since_change:.1f}s < {self.min_on_time}s)")
                    return self.current_output
            
            # If off and we want to turn on heating/cooling
            elif was_off and (is_heating or is_cooling):
                if time_since_change < self.min_off_time:
                    self.print(f"[HVAC_PID] Minimum off time not met ({time_since_change:.1f}s < {self.min_off_time}s)")
                    return self.current_output
        
        # Update last significant change time if we're making a mode change
        if ((was_heating and not is_heating) or (was_cooling and not is_cooling) or 
            (was_off and not is_off)):
            self.last_significant_output_time = current_time
        
        return desired_output

    # =============================================================================
    # PREDICTIVE CONTROL METHODS
    # =============================================================================
    
    def _get_future_setpoints(self, current_time_offset, horizon_seconds=60):
        """Get upcoming setpoints within the prediction horizon."""
        if not self.setpoint_schedule or not hasattr(self.setpoint_schedule, 'interpolated_setpoints'):
            return []
        
        future_setpoints = []
        for time_offset, temp in self.setpoint_schedule.interpolated_setpoints:
            if current_time_offset < time_offset <= current_time_offset + horizon_seconds:
                future_setpoints.append((time_offset, temp))
        
        return future_setpoints
    
    def _calculate_conservative_feedforward(self, current_temp, current_target, current_time_offset):
        """Conservative feedforward for HVAC applications."""
        if not self.setpoint_schedule:
            return 0
        
        future_setpoints = self._get_future_setpoints(current_time_offset, self.prediction_horizon)
        if not future_setpoints:
            return 0
        
        # Look for significant setpoint changes
        for time_offset, temp in future_setpoints:
            temp_change = temp - current_target
            if abs(temp_change) > 2.0:  # Only act on significant changes
                time_to_change = time_offset - current_time_offset
                if time_to_change > 0:
                    # Conservative feedforward - much smaller than direct PID
                    ff_gain = self.feedforward_gain * (1.0 - time_to_change / self.prediction_horizon)
                    return ff_gain * temp_change
        
        return 0

    # =============================================================================
    # LOGGING AND DIAGNOSTICS
    # =============================================================================
    
    def _log_pid_data(self, temp, setpoint, error, output, status, details=None):
        """Enhanced logging for HVAC PID debugging."""
        mode = "HEAT" if output > 0 else "COOL" if output < 0 else "OFF"
        
        log_data = {
            "pid_output": output,
            "current_temp": temp,
            "target_temp": setpoint,
            "error": error,
            "mode": mode,
            "status": status,
            "deadband": self.deadband
        }
        
        if details:
            log_data.update(details)
        
        self.notify(log_data)
        
        self.print(f"[HVAC_PID] {status} | Mode: {mode} | Temp: {temp:.2f}°C | Target: {setpoint:.2f}°C | Error: {error:.2f}°C | Output: {output:.1f}%")