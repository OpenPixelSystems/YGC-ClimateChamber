from typing import Optional, List

from app.backend.Dataclasses.Config import McuConfig, RelayConfig
from app.backend.Interfaces.IRelayController import IRelayController
from app.backend.Providers.gpio_provider import GPIO


class RelayController(IRelayController):
    def __init__(self, mcu_config: McuConfig):
        self.relay_configs: Optional[List[RelayConfig]] = []
        self.fridge_relay_pin: Optional[int] = None
        self.fridge_active: bool = False
        self.relay_config = mcu_config.relayModules
        self.initialize()

    def initialize(self) -> None:
        if self.relay_config is None:
            return

        # Initialize GPIO mode
        GPIO.setmode(GPIO.BCM)

        for relay_config in self.relay_config:
            self.relay_configs.append(relay_config)

            # Setup GPIO pin for relay
            GPIO.setup(relay_config.gpio_pin, GPIO.OUT)
            GPIO.output(relay_config.gpio_pin, GPIO.LOW)  # Start with relay OFF

            # Store fridge relay pin (assuming first relay is for fridge)
            if relay_config.name.lower() == "fridge" or self.fridge_relay_pin is None:
                self.fridge_relay_pin = relay_config.gpio_pin

        print(
            f"[RelayController] [initialize] Initialized {len(self.relay_configs)} relay(s), fridge on pin {self.fridge_relay_pin}"
        )

    def activate_fridge(self) -> None:
        if self.fridge_relay_pin is None:
            print("[RelayController] [activate_fridge] No fridge relay configured")
            return

        print(
            f"[RelayController] [activate_fridge] Activating fridge relay on pin {self.fridge_relay_pin}"
        )
        GPIO.output(self.fridge_relay_pin, GPIO.HIGH)
        self.fridge_active = True

    def deactivate_fridge(self) -> None:
        if self.fridge_relay_pin is None:
            print("[RelayController] [deactivate_fridge] No fridge relay configured")
            return

        print(
            f"[RelayController] [deactivate_fridge] Deactivating fridge relay on pin {self.fridge_relay_pin}"
        )
        GPIO.output(self.fridge_relay_pin, GPIO.LOW)
        self.fridge_active = False

    def is_fridge_active(self) -> bool:
        return self.fridge_active

    def cleanup(self) -> None:
        """Clean up GPIO resources"""
        print("[RelayController] [cleanup] Cleaning up relay controller")
        self.deactivate_fridge()
        GPIO.cleanup()
