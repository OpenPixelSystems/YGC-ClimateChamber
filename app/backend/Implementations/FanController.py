from typing import Optional, List

from app.backend.Dataclasses.Config import McuConfig
from app.backend.Interfaces.IFanController import IFanController
from app.backend.Modules.FanModule import FanModule
from app.backend.Interfaces.IFanModule import IFanModule


class FanController(IFanController):
    def __init__(self, mcu_config: McuConfig):
        self.fan_list: Optional[List[IFanModule]] = []
        self.fan_config = mcu_config.fanModules
        self.initialize()

    def initialize(self) -> None:
        if self.fan_config is None:
            return
        for fan_module_config in self.fan_config:
            self.fan_list.append(FanModule(fan_module_config))

    def activate(self) -> None:
        print(f"[FanController] [activate] Activating all fans")
        for fan in self.fan_list:
            fan.activate()

    def deactivate(self) -> None:
        print(f"[FanController] [activate] Deactivating all fans")
        for fan in self.fan_list:
            fan.deactivate()
