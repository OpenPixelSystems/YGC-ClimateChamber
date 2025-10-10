from abc import ABC, abstractmethod


class IRelayController(ABC):

    @abstractmethod
    def __init__(self):
        """Initialize the Relay controller."""
        pass

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the relay modules from config."""
        pass

    @abstractmethod
    def activate_fridge(self) -> None:
        """Activate the fridge relay for cooling."""
        pass

    @abstractmethod
    def deactivate_fridge(self) -> None:
        """Deactivate the fridge relay."""
        pass

    @abstractmethod
    def is_fridge_active(self) -> bool:
        """Check if the fridge relay is currently active."""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up GPIO resources."""
        pass
