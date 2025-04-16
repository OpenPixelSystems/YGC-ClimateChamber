import json
from app import app_state
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Union, Any

@dataclass
class GraphConfig:
    """Data class holding graph configuration parameters"""
    max_points: int
    min_x: float
    min_y: float
    max_y: float
    max_rico: float

class Graph:
    """Main graph model replicating original helper.py functionality"""
    def __init__(self, name, setpoints: List[Tuple[Union[int, float, str], Union[int, float, str]]], config_path=app_state.graph_config_path):
        # Convert setpoints to float tuples
        self.name = name
        self.setpoints = [(float(x), float(y)) for x, y in setpoints]
        self.config = self._load_config(Path(config_path))
        self.valid_dataset = self._validate_dataset()

    def _load_config(self, config_path: Path) -> GraphConfig:
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)
                f.close()
                return GraphConfig(
                    max_points=int(config_data["max_points"]["value"]),
                    min_x=float(config_data["min_x"]["value"]),
                    min_y=float(config_data["min_y"]["value"]),
                    max_y=float(config_data["max_y"]["value"]),
                    max_rico=float(config_data["max_rico"]["value"])
                )

        except (FileNotFoundError, KeyError, json.JSONDecodeError, ValueError) as e:
            raise RuntimeError(f"Configuration error: {str(e)}")

    def _validate_dataset(self) -> Tuple[bool, str]:
        """Validate the temperature profile dataset"""
        try:
            # Check if the dataset exceeds the max number of points
            if len(self.setpoints) > self.config.max_points:
                return False, "Dataset heeft te veel punten."

            # Check if all points are within the limits
            for i, (x, y) in enumerate(self.setpoints):
                if x < self.config.min_x or y < self.config.min_y or y > self.config.max_y:
                    return False, f"Punt {i} ({x}, {y}) ligt buiten de limieten."

            # Check if time progression and slope are realistic
            for i in range(1, len(self.setpoints)):
                x1, y1 = self.setpoints[i - 1]
                x2, y2 = self.setpoints[i]
                if x2 <= x1:
                    return False, f"Punten {i - 1} en {i} hebben een niet-realistische tijdssprong."
                slope = abs((y2 - y1) / (x2 - x1))
                if slope > self.config.max_rico:
                    return False, f"Helling tussen punten {i - 1} en {i} is te groot: {slope} > {self.config.max_rico}."

            # If all checks pass
            return True, None
            
        except (TypeError, ValueError) as e:
            return False, f"Invalid data format: {str(e)}"

    def add_setpoint(self, x: Union[int, float, str], y: Union[int, float, str]) -> None:
        """Add a new setpoint"""
        self.setpoints.append((float(x), float(y)))

    def remove_setpoint(self, index: int) -> None:
        """Remove setpoint by index"""
        if 0 <= index < len(self.setpoints):
            del self.setpoints[index]
        else:
            raise IndexError("Invalid setpoint index")

    def clear_setpoints(self) -> None:
        """Clear all setpoints"""
        self.setpoints.clear()

    def __str__(self) -> str:
        """String representation matching original"""
        return f"Graph with setpoints: {self.setpoints}"