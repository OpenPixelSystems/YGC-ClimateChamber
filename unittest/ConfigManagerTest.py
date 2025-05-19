import unittest
from pathlib import Path

from app.backend.Implementations.ConfigManager import ConfigManager

class TestConfigManager(unittest.TestCase):
    def setUp(self):
        # Get the project root directory (where the unittest folder is located)
        self.project_root = Path(__file__).parent.parent
        self.config_dir = self.project_root / 'app' / 'backend' / 'config'
        
        # Define config file paths
        self.graph_config_path = self.config_dir / 'graph_config.json'
        self.control_config_path = self.config_dir / 'control_config.json'
        self.mcu_config_path = self.config_dir / 'raspberry_pi_config.json'
        
        # Initialize ConfigManager
        self.config_manager = ConfigManager(
            control_config_path=self.control_config_path,
            graph_config_path=self.graph_config_path,
            mcu_config_path=self.mcu_config_path
        )

    def test_control_config_loading(self):
        """Test if control config is loaded correctly"""
        self.assertIsNotNone(self.config_manager.control_config)
        self.assertIsInstance(self.config_manager.control_config.kp, float)
        self.assertIsInstance(self.config_manager.control_config.ki, float)
        self.assertIsInstance(self.config_manager.control_config.kd, float)
        self.assertIsInstance(self.config_manager.control_config.read_delay, float)

    def test_graph_config_loading(self):
        """Test if graph config is loaded correctly"""
        self.assertIsNotNone(self.config_manager.graph_config)
        self.assertIsInstance(self.config_manager.graph_config.max_points, int)
        self.assertIsInstance(self.config_manager.graph_config.min_x, int)
        self.assertIsInstance(self.config_manager.graph_config.min_y, float)
        self.assertIsInstance(self.config_manager.graph_config.max_y, float)
        self.assertIsInstance(self.config_manager.graph_config.max_rico, float)

    def test_mcu_config_loading(self):
        """Test if MCU config is loaded correctly"""
        self.assertIsNotNone(self.config_manager.mcu_config)
        self.assertIsInstance(self.config_manager.mcu_config.sensors, list)
        
        # Test if Sensors are loaded correctly
        for sensor in self.config_manager.mcu_config.sensors:
            self.assertIsNotNone(sensor.name)
            self.assertIsNotNone(sensor.type)
            self.assertIsNotNone(sensor.gpio_pin)
            self.assertIsNotNone(sensor.max_temp)
            self.assertIsNotNone(sensor.min_temp)
            self.assertIsNotNone(sensor.unit)

if __name__ == '__main__':
    unittest.main()