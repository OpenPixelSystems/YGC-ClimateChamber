from dataclasses import dataclass
from typing import Optional, Tuple, List, Dict, Any, Union

from app.backend.Interfaces.IConfigManager import IConfigManager
from app.backend.Implementations.ClimateChamberController import (
    ClimateChamberController,
)
from app.routes.Helper.graph import Graph


@dataclass
class TemperatureValidationResult:
    is_valid: bool
    message: Optional[str] = None
    value: Optional[float] = None


class TemperatureService:
    """Service for managing temperature-related operations"""

    def __init__(
        self, config_manager: IConfigManager, controller: ClimateChamberController
    ):
        self.config_manager = config_manager
        self.controller = controller

    def validate_temperature(
        self, temp_value: Union[int, float, str]
    ) -> TemperatureValidationResult:
        """Validate a single temperature value against configuration limits"""
        try:
            temperature = float(temp_value)
            config = self.config_manager.graph_config
            min_temp = config.min_y
            max_temp = config.max_y

            if not (min_temp <= temperature <= max_temp):
                return TemperatureValidationResult(
                    is_valid=False,
                    message=f"Temperature must be between {min_temp}°C and {max_temp}°C",
                )

            return TemperatureValidationResult(is_valid=True, value=temperature)

        except ValueError:
            return TemperatureValidationResult(
                is_valid=False, message="Invalid temperature value"
            )

    def set_constant_temperature(
        self, temperature: Union[int, float, str]
    ) -> TemperatureValidationResult:
        """Set a constant temperature target"""
        validation = self.validate_temperature(temperature)
        if not validation.is_valid:
            return validation

        try:
            self.controller.desired_flow_graph = Graph(
                "desired_temperature", [(0, float(temperature))], self.config_manager
            )
            return TemperatureValidationResult(
                is_valid=True,
                value=float(temperature),
                message=f"Temperature set to {temperature}°C",
            )
        except (ValueError, TypeError) as e:
            return TemperatureValidationResult(
                is_valid=False, message=f"Error setting temperature: {str(e)}"
            )

    def set_temperature_profile(
        self, points: List[Dict[str, Any]]
    ) -> Tuple[bool, str, Optional[Graph]]:
        """Set a temperature profile from a list of points"""
        try:
            # Convert points to the format expected by Graph
            tuple_list = [(float(point["x"]), float(point["y"])) for point in points]

            # Create and validate the graph`
            graph = Graph("desired_temperature", tuple_list, self.config_manager)
            is_valid = graph.valid_dataset
            message = graph.validation_message

            if not is_valid:
                return False, f"Invalid dataset: {message}", None

            self.controller.desired_flow_graph = graph
            return True, "Temperature profile set successfully", graph

        except (KeyError, TypeError, ValueError) as e:
            return False, f"Invalid data format: {str(e)}", None
        except Exception as e:
            return False, f"An error occurred: {str(e)}", None
