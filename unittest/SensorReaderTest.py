import unittest
import os
import json
import tempfile
from unittest.mock import patch, mock_open

# Import the modules we want to test
from app.backend.services.SensorReader import SensorReader, Sensor, DS18B20_read, DHT22_read

class TestSensorReader(unittest.TestCase):

    def setUp(self):
        # Create a temporary config file for testing
        self.test_config = {
            "_comment": "Test configuration",
            "Test_Sensor1": {
                "name": "Test_Sensor1",
                "type": "temperature",
                "editable": {
                    "gpio_pin": 12,
                    "max_temp": 100,
                    "min_temp": -10
                },
                "unit": "degrees",
                "_comment": "Test temperature sensor"
            },
            "Test_Sensor2": {
                "name": "Test_Sensor2",
                "type": "humidity",
                "editable": {
                    "gpio_pin": 14,
                    "max_temp": 120,
                    "min_temp": -40
                },
                "unit": "degrees",
                "_comment": "Test humidity sensor"
            }
        }

        # Create a temporary file with our test config
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, mode='w')
        json.dump(self.test_config, self.temp_file)
        self.temp_file.close()

        # Create a sensor reader with our test config
        self.reader = SensorReader(self.temp_file.name)

    def tearDown(self):
        # Clean up the temporary file
        os.unlink(self.temp_file.name)

    def test_initialization(self):
        """Test that the sensor reader initializes properly"""
        self.reader.initialise()

        # We should have 2 sensors
        self.assertEqual(len(self.reader.sensor_list), 2)

        # Check the first sensor
        sensor1 = next((s for s in self.reader.sensor_list if s._name == "Test_Sensor1"), None)
        self.assertIsNotNone(sensor1)
        self.assertEqual(sensor1._type, "temperature")
        self.assertEqual(sensor1._pin, 12)

        # Check the second sensor
        sensor2 = next((s for s in self.reader.sensor_list if s._name == "Test_Sensor2"), None)
        self.assertIsNotNone(sensor2)
        self.assertEqual(sensor2._type, "humidity")
        self.assertEqual(sensor2._pin, 14)

    def test_invalid_config(self):
        """Test handling of invalid configuration"""
        # Create reader with non-existent file
        bad_reader = SensorReader("nonexistent_file.json")

        # Should raise RuntimeError
        with self.assertRaises(RuntimeError):
            bad_reader.initialise()

    @patch('os.path.exists')
    def test_ds18b20_read_mock(self, mock_exists):
        """Test DS18B20 read function in mock mode"""
        # Force mock mode
        mock_exists.return_value = False

        # Create a test sensor
        sensor_info = self.test_config["Test_Sensor1"]
        sensor = Sensor("Test_Sensor1", sensor_info)

        # Read the sensor
        result = DS18B20_read(sensor)

        # We should get a simulated reading
        self.assertIn("Test_Sensor1", result)
        self.assertIsNotNone(result["Test_Sensor1"])
        self.assertIsInstance(result["Test_Sensor1"], (int, float))

    @patch('os.path.exists')
    @patch('os.listdir')
    @patch('builtins.open', new_callable=mock_open, read_data='YES\nt=22500')
    def test_ds18b20_read_real(self, mock_file, mock_listdir, mock_exists):
        """Test DS18B20 read function in real mode with mocked hardware"""
        # Simulate real Raspberry Pi
        mock_exists.return_value = True
        mock_listdir.return_value = ['28-0000123456789']

        # Create a test sensor
        sensor_info = self.test_config["Test_Sensor1"]
        sensor = Sensor("Test_Sensor1", sensor_info)

        # Read the sensor
        result = DS18B20_read(sensor)

        # Should get mocked temperature of 22.5°C
        self.assertEqual(result["Test_Sensor1"], 22.5)

    @patch('os.path.exists')
    def test_dht22_read_mock(self, mock_exists):
        """Test DHT22 read function in mock mode"""
        # Force mock mode
        mock_exists.return_value = False

        # Create a test sensor
        sensor_info = self.test_config["Test_Sensor1"]
        sensor = Sensor("Test_Sensor1", sensor_info)

        # Read the sensor
        result = DHT22_read(sensor)

        # We should get a simulated reading
        self.assertIn("Test_Sensor1", result)
        self.assertIsNotNone(result["Test_Sensor1"])
        self.assertIsInstance(result["Test_Sensor1"], (int, float))

    def test_read_sensors(self):
        """Test reading all sensors"""
        self.reader.initialise()
        readings = self.reader.read_sensors()

        # Should have readings for both sensors
        self.assertEqual(len(readings), 2)
        self.assertIn("Test_Sensor1", readings)
        self.assertIn("Test_Sensor2", readings)

    @patch('app.backend.services.SensorReader.DS18B20_read')
    @patch('app.backend.services.SensorReader.DHT22_read')
    def test_read_sensors_with_mocks(self, mock_dht22, mock_ds18b20):
        """Test reading sensors with mocked read functions"""
        # Set up mock return values
        mock_ds18b20.return_value = {"Test_Sensor1": 22.5}
        mock_dht22.return_value = {"Test_Sensor2": 45.0}

        self.reader.initialise()
        readings = self.reader.read_sensors()

        # Verify our mock functions were called with the right sensors
        self.assertEqual(mock_ds18b20.call_count + mock_dht22.call_count, 2)

        # Verify the readings
        self.assertEqual(readings["Test_Sensor1"], 22.5)
        self.assertEqual(readings["Test_Sensor2"], 45.0)


if __name__ == '__main__':
    unittest.main()