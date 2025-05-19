import unittest
from unittest.mock import Mock, patch

from app.backend.Implementations.SensorReader import SensorReader
from app.backend.Implementations.ConfigManager import McuConfig, SensorConfig


class TestSensorReader(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create test MCU config with mock Sensors
        self.mcu_config = McuConfig()
        self.sensors = [
            SensorConfig(
                name="Temp_sensor_1",
                type="temperature",
                gpio_pin=1,
                max_temp=20,
                min_temp=0,
                unit="degrees"
            ),
            SensorConfig(
                name="Temp_sensor_2",
                type="temperature",
                gpio_pin=12,
                max_temp=40,
                min_temp=0,
                unit="degrees"
            )
        ]
        self.mcu_config.sensors = self.sensors

    def test_initialization(self):
        """Test if SensorReader initializes correctly with MCU config."""
        sensor_reader = SensorReader(self.mcu_config)
        self.assertEqual(len(sensor_reader.sensor_list), 2)
        self.assertEqual(sensor_reader.sensor_list[0]._name, "Temp_sensor_1")
        self.assertEqual(sensor_reader.sensor_list[1]._name, "Temp_sensor_2")

    def test_initialization_error(self):
        """Test if SensorReader handles initialization errors correctly."""
        with self.assertRaises(RuntimeError):
            # Pass None instead of McuConfig to trigger error
            SensorReader(None)

    def test_subscribe_unsubscribe(self):
        """Test subscription and unsubscription of listeners."""
        sensor_reader = SensorReader(self.mcu_config)
        mock_callback = Mock()
        
        # Test subscription
        sensor_reader.subscribe(mock_callback)
        self.assertIn(mock_callback, sensor_reader.listeners)
        
        # Test unsubscription
        sensor_reader.unsubscribe(mock_callback)
        self.assertNotIn(mock_callback, sensor_reader.listeners)

    def test_notify(self):
        """Test if listeners are notified with sensor readings."""
        sensor_reader = SensorReader(self.mcu_config)
        mock_callback = Mock()
        sensor_reader.subscribe(mock_callback)
        
        test_data = {"Temp_sensor_1": 25.5, "Temp_sensor_2": 30.0}
        sensor_reader.notify(test_data)
        
        mock_callback.assert_called_once_with(test_data)

    @patch('app.backend.Implementations.Sensor.Sensor.read_sensor')
    def test_read_sensors(self, mock_read_sensor):
        """Test reading from all Sensors."""
        sensor_reader = SensorReader(self.mcu_config)
        
        # Mock sensor readings
        mock_read_sensor.side_effect = [
            {"Temp_sensor_1": 25.5},
            {"Temp_sensor_2": 30.0}
        ]
        
        # Create a mock callback
        mock_callback = Mock()
        sensor_reader.subscribe(mock_callback)
        
        # Read Sensors
        readings = sensor_reader.read_sensors()
        
        # Verify results
        self.assertEqual(readings["Temp_sensor_1"], 25.5)
        self.assertEqual(readings["Temp_sensor_2"], 30.0)
        mock_callback.assert_called_once_with(readings)
        self.assertEqual(mock_read_sensor.call_count, 2)

    def test_empty_sensor_list(self):
        """Test behavior with empty sensor list."""
        empty_config = McuConfig()
        empty_config.sensors = []
        sensor_reader = SensorReader(empty_config)
        
        readings = sensor_reader.read_sensors()
        self.assertEqual(readings, {})


if __name__ == '__main__':
    unittest.main()
