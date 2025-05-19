from abc import ABC, abstractmethod

from app.backend.Dataclasses.Config import ControlConfig, GraphConfig, McuConfig


class IConfigManager(ABC):
    """Interface for configuration management in the application."""

    @property
    @abstractmethod
    def control_config(self) -> ControlConfig:
        """Get the control configuration."""
        pass

    @property
    @abstractmethod
    def graph_config(self) -> GraphConfig:
        """Get the graph configuration."""
        pass

    @property
    @abstractmethod
    def mcu_config(self) -> McuConfig:
        """Get the MCU configuration."""
        pass

    @abstractmethod
    def reload_config(self) -> None:
        """Reload all configurations from their respective files."""
        pass