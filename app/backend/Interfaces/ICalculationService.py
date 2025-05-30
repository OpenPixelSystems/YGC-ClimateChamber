from abc import ABC, abstractmethod

class ICalculationService(ABC):
    """Interface defining the contract for any climate chamber controller implementation."""


    @abstractmethod
    def calculate_pid_control(self, current_temp: float, target_temp: float) -> float:
        """Apply PID control based on current and target temperatures.

        Args:
            current_temp: Current temperature reading
            target_temp: Target temperature to achieve

        Returns:
            float: The control output value
        """
        pass

    @abstractmethod
    def pause(self, current_temp: float, target_temp: float):
        """Pause the calculation."""
        pass

    def stop(self):
        pass