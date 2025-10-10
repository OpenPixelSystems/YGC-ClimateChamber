from abc import ABC, abstractmethod
from typing import Generator

from app.routes.Helper.graph import Graph


class IClimateChamberController(ABC):
    """Interface defining the contract for any climate chamber controller implementation."""

    @abstractmethod
    def set_desired_graph(self, graph: Graph) -> None:
        """Set the desired temperature profile.

        Args:
            graph: The graph object containing the desired temperature profile
        """
        pass

    @abstractmethod
    def start_sensor_stream(self) -> None:
        """Start the sensor data stream and control loop."""
        pass

    @abstractmethod
    def stop_sensor_stream(self) -> None:
        """Stop the sensor data stream and control loop."""
        pass

    @abstractmethod
    def sensor_data_provider(self) -> Generator[str, None, None]:
        """Generator function for Server-Sent Events (SSE).

        Yields:
            JSON-formatted string containing sensor data and control information
        """
        pass
