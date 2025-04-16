from dataclasses import dataclass
from typing import Optional, Tuple, List, Dict, Any, Union
from app.backend.models.graph import Graph
from app.backend.services.config import load_config, get_config_value
from app import app_state

@dataclass
class TemperatureValidationResult:
    is_valid: bool
    message: Optional[str] = None
    value: Optional[float] = None

class TemperatureService:
    """Service for managing temperature-related operations"""
    
    @staticmethod
    def validate_temperature(temp_value: Union[int, float, str]) -> TemperatureValidationResult:
        """Validate a single temperature value against configuration limits"""
        try:
            temperature = float(temp_value)
            config = load_config(app_state.graph_config_path)
            min_temp = float(get_config_value(config, 'min_y', 0))
            max_temp = float(get_config_value(config, 'max_y', 100))

            if not (min_temp <= temperature <= max_temp):
                return TemperatureValidationResult(
                    is_valid=False,
                    message=f'Temperature must be between {min_temp}°C and {max_temp}°C'
                )
            
            return TemperatureValidationResult(
                is_valid=True,
                value=temperature
            )
            
        except ValueError:
            return TemperatureValidationResult(
                is_valid=False,
                message='Invalid temperature value'
            )

    @staticmethod
    def set_constant_temperature(temperature: Union[int, float, str]) -> TemperatureValidationResult:
        """Set a constant temperature target"""
        validation = TemperatureService.validate_temperature(temperature)
        if not validation.is_valid:
            return validation
            
        try:
            app_state.desired_flow_graph = Graph('desired_temperature', [(0, float(temperature))])
            return TemperatureValidationResult(
                is_valid=True,
                value=float(temperature),
                message=f'Temperature set to {temperature}°C'
            )
        except (ValueError, TypeError) as e:
            return TemperatureValidationResult(
                is_valid=False,
                message=f'Error setting temperature: {str(e)}'
            )

    @staticmethod
    def set_temperature_profile(points: List[Dict[str, Any]]) -> Tuple[bool, str, Optional[Graph]]:
        """Set a temperature profile from a list of points"""
        try:
            # Convert points to the format expected by Graph
            tuple_list = [
                (float(point['x']), float(point['y'])) 
                for point in points
            ]
            
            # Create and validate the graph
            graph = Graph('desired_temperature', tuple_list)
            is_valid, message = graph.valid_dataset
            
            if not is_valid:
                return False, f"Invalid dataset: {message}", None

            app_state.desired_flow_graph = graph
            return True, "Temperature profile set successfully", graph
            
        except (KeyError, TypeError, ValueError) as e:
            return False, f"Invalid data format: {str(e)}", None
        except Exception as e:
            return False, f"An error occurred: {str(e)}", None

# Single instance for the application
temperature_service = TemperatureService()
