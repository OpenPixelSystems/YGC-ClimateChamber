"""
FlowExecutor class for managing and executing temperature flow diagrams.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import logging


class FlowExecutor:
    """
    Handles execution of temperature flow diagrams created in the flow designer.
    Stores execution flow data and provides interface for climate chamber control.
    """

    def __init__(self, execution_flow: Dict[str, Any], full_flow_data: Dict[str, Any]):
        """
        Initialize FlowExecutor with flow data.

        Args:
            execution_flow: Processed execution steps from flow designer
            full_flow_data: Complete flow data including visual information
        """
        self.execution_flow = execution_flow
        self.full_flow_data = full_flow_data
        self.current_step_index = 0
        self.is_executing = False
        self.start_time: Optional[datetime] = None
        self.logger = logging.getLogger(__name__)

        # Store initial/current temperature when start node executes
        self.initial_temperature: Optional[float] = None

        # Validate flow data
        self._validate_flow_data()

    def _validate_flow_data(self) -> None:
        """Validate the execution flow data structure."""
        required_keys = ['version', 'flowId', 'executionSteps', 'metadata']
        for key in required_keys:
            if key not in self.execution_flow:
                raise ValueError(f"Missing required key in execution flow: {key}")

        if not self.execution_flow['executionSteps']:
            raise ValueError("Execution flow must contain at least one step")

    @property
    def flow_id(self) -> str:
        """Get the flow ID."""
        return self.execution_flow.get('flowId', 'unknown')

    @property
    def total_steps(self) -> int:
        """Get total number of execution steps."""
        return len(self.execution_flow['executionSteps'])

    @property
    def estimated_duration(self) -> int:
        """Get estimated duration in minutes."""
        return self.execution_flow['metadata'].get('estimatedDurationMinutes', 0)

    @property
    def current_step(self) -> Optional[Dict[str, Any]]:
        """Get the current execution step."""
        if 0 <= self.current_step_index < len(self.execution_flow['executionSteps']):
            return self.execution_flow['executionSteps'][self.current_step_index]
        return None

    @property
    def progress_percentage(self) -> float:
        """Get execution progress as percentage."""
        if self.total_steps == 0:
            return 0.0
        # When execution is complete or on the last step (end node), show 100%
        if not self.is_executing or self.current_step_index >= self.total_steps - 1:
            current_step = self.current_step
            if current_step and current_step.get('stepType') == 'end-node':
                return 100.0
        return (self.current_step_index / self.total_steps) * 100

    def get_execution_steps(self) -> List[Dict[str, Any]]:
        """Get all execution steps."""
        return self.execution_flow['executionSteps']

    def get_step_by_index(self, index: int) -> Optional[Dict[str, Any]]:
        """Get specific step by index."""
        if 0 <= index < len(self.execution_flow['executionSteps']):
            return self.execution_flow['executionSteps'][index]
        return None

    def start_execution(self) -> None:
        """Start flow execution."""
        if self.is_executing:
            raise RuntimeError("Flow is already executing")

        self.is_executing = True
        self.current_step_index = 0
        self.start_time = datetime.now()
        self.logger.info(f"Started flow execution: {self.flow_id}")

    def advance_to_next_step(self) -> bool:
        """
        Advance to the next execution step.

        Returns:
            bool: True if advanced successfully, False if no more steps
        """
        if not self.is_executing:
            raise RuntimeError("Flow is not currently executing")

        if self.current_step_index < len(self.execution_flow['executionSteps']) - 1:
            self.current_step_index += 1
            self.logger.info(f"Advanced to step {self.current_step_index + 1} of {self.total_steps}")
            return True
        return False

    def stop_execution(self) -> None:
        """Stop flow execution."""
        self.is_executing = False
        self.logger.info(f"Stopped flow execution: {self.flow_id}")

    def reset_execution(self) -> None:
        """Reset execution to beginning."""
        self.current_step_index = 0
        self.is_executing = False
        self.start_time = None
        self.logger.info(f"Reset flow execution: {self.flow_id}")

    def get_execution_status(self) -> Dict[str, Any]:
        """
        Get current execution status.

        Returns:
            Dictionary containing execution status information
        """
        return {
            'flowId': self.flow_id,
            'isExecuting': self.is_executing,
            'currentStepIndex': self.current_step_index,
            'totalSteps': self.total_steps,
            'progressPercentage': self.progress_percentage,
            'currentStep': self.current_step,
            'startTime': self.start_time.isoformat() if self.start_time else None,
            'estimatedDuration': self.estimated_duration,
            'initialTemperature': self.initial_temperature
        }

    def get_target_temperature(self) -> Optional[float]:
        """
        Get the target temperature for the current step.

        Returns:
            float: Target temperature in Celsius, or None if no target (e.g., start node)
        """
        if not self.is_executing:
            return None

        current_step = self.current_step
        if not current_step:
            return None

        target_temp = current_step.get('targetTemperature')

        # If targetTemperature is None and readCurrentTemperature is True,
        # use the initial temperature captured from start node
        if target_temp is None and current_step.get('readCurrentTemperature'):
            return self.initial_temperature

        return target_temp

    def should_advance_step(self, current_temp: float, elapsed_time: float) -> bool:
        """
        Determine if the flow should advance to the next step based on current conditions.

        Args:
            current_temp: Current average chamber temperature
            elapsed_time: Time elapsed since flow start in seconds

        Returns:
            bool: True if should advance to next step
        """
        if not self.is_executing:
            return False

        current_step = self.current_step
        if not current_step:
            return False

        step_type = current_step.get('stepType')

        if step_type == 'start-node':
            # Capture initial temperature when start node is active
            if self.initial_temperature is None:
                self.initial_temperature = current_temp
                self.logger.info(f"Captured initial temperature: {current_temp}°C")
            # Start node advances immediately after reading current temperature
            return True

        elif step_type == 'temperature-goal':
            # Check if target temperature is reached within tolerance
            target_temp = current_step.get('targetTemperature')
            tolerance = current_step.get('tolerance', 0.5)

            if target_temp is not None:
                temp_diff = abs(current_temp - target_temp)
                return temp_diff <= tolerance

        elif step_type == 'temperature-hold':
            # Check if hold duration has elapsed
            duration_minutes = current_step.get('duration', 0)
            duration_seconds = duration_minutes * 60

            # Get step start time (when this step became active)
            step_start_time = elapsed_time - (duration_seconds if elapsed_time >= duration_seconds else elapsed_time)
            step_elapsed = elapsed_time - step_start_time

            return step_elapsed >= duration_seconds

        elif step_type == 'end-node':
            # End node stops execution
            return False

        return False

    def get_control_action(self) -> str:
        """
        Get the control action for the current step.

        Returns:
            str: 'initialize', 'heat', 'cool', 'hold', or 'complete'
        """
        if not self.is_executing:
            return 'complete'

        current_step = self.current_step
        if not current_step:
            return 'complete'

        step_type = current_step.get('stepType')
        action = current_step.get('action', 'hold')

        if step_type == 'start-node':
            return 'initialize'
        elif step_type == 'end-node':
            return 'complete'
        else:
            return action  # 'reach_temperature' or 'hold_temperature'

    def get_temperature_target_for_step(self, step_index: int) -> Optional[float]:
        """
        Get target temperature for a specific step.

        Args:
            step_index: Index of the step

        Returns:
            Target temperature in Celsius, or None if not applicable
        """
        step = self.get_step_by_index(step_index)
        if step and 'targetTemperature' in step:
            return step['targetTemperature']
        return None

    def get_current_temperature_target(self) -> Optional[float]:
        """Get target temperature for current step."""
        return self.get_temperature_target_for_step(self.current_step_index)

    def get_tolerance_for_step(self, step_index: int) -> Optional[float]:
        """
        Get temperature tolerance for a specific step.

        Args:
            step_index: Index of the step

        Returns:
            Temperature tolerance in Celsius, or None if not applicable
        """
        step = self.get_step_by_index(step_index)
        if step and 'tolerance' in step:
            return step['tolerance']
        return None

    def get_current_tolerance(self) -> Optional[float]:
        """Get temperature tolerance for current step."""
        return self.get_tolerance_for_step(self.current_step_index)

    def to_dict(self) -> Dict[str, Any]:
        """Convert FlowExecutor to dictionary for serialization."""
        return {
            'execution_flow': self.execution_flow,
            'full_flow_data': self.full_flow_data,
            'current_step_index': self.current_step_index,
            'is_executing': self.is_executing,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'initial_temperature': self.initial_temperature
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FlowExecutor':
        """Create FlowExecutor from dictionary."""
        executor = cls(data['execution_flow'], data['full_flow_data'])
        executor.current_step_index = data.get('current_step_index', 0)
        executor.is_executing = data.get('is_executing', False)
        executor.initial_temperature = data.get('initial_temperature')
        if data.get('start_time'):
            executor.start_time = datetime.fromisoformat(data['start_time'])
        return executor