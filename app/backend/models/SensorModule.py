from abc import ABC

from app.backend.models.interfaces.ISensorModule import *

class SensorModule(ISensorModule):
    _instance = None  # Singleton instance

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(SensorModule, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        #TODO create config file to initialise and dynamically add sensors to the list, sensors get read out dynamically. Peltier sensors should be cleary distinct from other sensors (needed for peltier steering)
        pass

    @abstractmethod
    def get_sensors(self):
        return None
        # Real implementation

