"""
Temperature Simulation Service
Provides realistic temperature simulation based on PID control output for testing purposes.
"""

import time
import threading
from typing import Optional


class TemperatureSimulationService:
    """Simulates realistic temperature behavior based on PID control output."""

    def __init__(self):
        """Initialize the temperature simulation service."""
        # Simulation parameters
        self.current_temperature = 20.0  # Starting room temperature
        self.ambient_temperature = 20.0  # Room temperature
        self.last_update_time = time.time()

        # Physical simulation parameters - tuned for climate chamber behavior
        self.thermal_mass = 30.0  # Thermal inertia (reduced for faster response)
        self.heating_efficiency = (
            0.3  # How efficiently PID output converts to temperature change (increased)
        )
        self.cooling_efficiency = (
            0.15  # Natural cooling rate when PID output is low (increased)
        )
        self.heat_loss_coefficient = (
            0.01  # Heat loss to ambient (reduced for better heat retention)
        )
        self.max_heating_rate = (
            1.0  # Maximum °C/second when PID = 100% (increased significantly)
        )
        self.max_cooling_rate = 1.0  # Maximum °C/second when PID = -100% (increased)

        # Current control state
        self.current_pid_output = 0.0
        self.last_pid_output = 0.0

        # Thread safety
        self._lock = threading.Lock()

        print("[TemperatureSimulation] Initialized with physics-based simulation")

    def update_pid_output(self, pid_output: float) -> None:
        """Update the current PID output that affects temperature simulation.

        Args:
            pid_output: PID control output percentage (-100 to 100)
        """
        with self._lock:
            self.last_pid_output = self.current_pid_output
            self.current_pid_output = max(-100.0, min(100.0, pid_output))
            print(
                f"[TemperatureSimulation] PID output updated: {self.current_pid_output}% (current temp: {self.current_temperature:.1f}°C)"
            )

    def get_simulated_temperature(
        self, sensor_name: str, min_temp: float = -20.0, max_temp: float = 180.0
    ) -> float:
        """Get simulated temperature based on current PID output and physics.

        Args:
            sensor_name: Name of the sensor (for different behaviors)
            min_temp: Minimum allowed temperature
            max_temp: Maximum allowed temperature

        Returns:
            Simulated temperature with realistic physics behavior
        """
        with self._lock:
            current_time = time.time()
            dt = current_time - self.last_update_time

            # Limit time step to prevent unrealistic jumps (max 5 seconds)
            dt = min(dt, 5.0)

            if dt > 0:
                # Calculate temperature change based on PID output and physics
                temp_change = self._calculate_temperature_change(dt)

                # Apply the change
                self.current_temperature += temp_change

                # Apply bounds
                self.current_temperature = max(
                    min_temp, min(max_temp, self.current_temperature)
                )

                # Add small random noise for realism
                import random

                noise = random.uniform(-0.1, 0.1)
                self.current_temperature += noise

                self.last_update_time = current_time

            # Different sensor types can have slight offsets
            sensor_offset = self._get_sensor_offset(sensor_name)

            return round(self.current_temperature + sensor_offset, 1)

    def _calculate_temperature_change(self, dt: float) -> float:
        """Calculate temperature change based on PID output and thermal physics.

        Args:
            dt: Time step in seconds

        Returns:
            Temperature change in degrees Celsius
        """
        # Current temperature difference from ambient
        temp_diff = self.current_temperature - self.ambient_temperature

        # PID output effect (heating/cooling)
        if self.current_pid_output > 0:
            # Heating mode
            heating_power = (self.current_pid_output / 100.0) * self.max_heating_rate
            pid_effect = heating_power * self.heating_efficiency
        else:
            # Cooling mode (negative PID output)
            cooling_power = abs(self.current_pid_output / 100.0) * self.max_cooling_rate
            pid_effect = -cooling_power * self.cooling_efficiency

        # Natural heat loss to ambient (always present)
        heat_loss = -temp_diff * self.heat_loss_coefficient

        # Total temperature change rate (°C/second)
        total_rate = pid_effect + heat_loss

        # Apply thermal mass (makes temperature change more gradual)
        thermal_dampening = 1.0 / (1.0 + self.thermal_mass * 0.01)
        actual_rate = total_rate * thermal_dampening

        # Calculate actual temperature change over time step
        temp_change = actual_rate * dt

        # Debug output every 10 seconds (approximately)
        if hasattr(self, "_debug_counter"):
            self._debug_counter += 1
        else:
            self._debug_counter = 0

        if self._debug_counter % 50 == 0:  # Print every ~50 calls (about 10 seconds)
            print(
                f"[TemperatureSimulation] Debug: PID={self.current_pid_output}%, temp={self.current_temperature:.1f}°C, "
                f"pid_effect={pid_effect:.3f}, heat_loss={heat_loss:.3f}, total_rate={total_rate:.3f}, "
                f"temp_change={temp_change:.3f}"
            )

        return temp_change

    def _get_sensor_offset(self, sensor_name: str) -> float:
        """Get a small offset for sensor variation.

        Args:
            sensor_name: Name of the sensor

        Returns:
            Small offset to simulate sensor variation
        """
        # Create consistent but different offsets for different sensors
        # This simulates slight calibration differences between sensors
        name_hash = hash(sensor_name) % 1000
        offset = (name_hash / 1000.0 - 0.5) * 0.4  # ±0.2°C variation
        return offset

    def reset_simulation(self, initial_temp: float = 20.0) -> None:
        """Reset simulation to initial conditions.

        Args:
            initial_temp: Starting temperature
        """
        with self._lock:
            self.current_temperature = initial_temp
            self.current_pid_output = 0.0
            self.last_pid_output = 0.0
            self.last_update_time = time.time()
            print(f"[TemperatureSimulation] Reset to {initial_temp}°C")

    def set_ambient_temperature(self, ambient_temp: float) -> None:
        """Set the ambient (room) temperature.

        Args:
            ambient_temp: Ambient temperature in Celsius
        """
        with self._lock:
            self.ambient_temperature = ambient_temp
            print(
                f"[TemperatureSimulation] Ambient temperature set to {ambient_temp}°C"
            )

    def get_simulation_info(self) -> dict:
        """Get current simulation state for debugging.

        Returns:
            Dictionary with current simulation parameters
        """
        with self._lock:
            return {
                "current_temperature": self.current_temperature,
                "current_pid_output": self.current_pid_output,
                "ambient_temperature": self.ambient_temperature,
                "thermal_mass": self.thermal_mass,
                "heating_efficiency": self.heating_efficiency,
                "cooling_efficiency": self.cooling_efficiency,
            }


# Global instance for shared use across sensors
_simulation_service: Optional[TemperatureSimulationService] = None


def get_temperature_simulation_service() -> TemperatureSimulationService:
    """Get the global temperature simulation service instance.

    Returns:
        Shared TemperatureSimulationService instance
    """
    global _simulation_service
    if _simulation_service is None:
        _simulation_service = TemperatureSimulationService()
    return _simulation_service
