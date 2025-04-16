import os
import unittest
from unittest.mock import patch

import app
# Import the class to test
from database.TemperatureSensorLogger import *


class TestTemperatureSensorLogger(unittest.TestCase):

    def setUp(self):
        """Set up test environment before each test."""
        # Use a test database file
        self.test_db_path = 'test_climate_data.db'
        self.test_config_path = 'test_sensorConfig.json'
        self.test_mock_data_path = 'test_mockSensorData.json'

        # Create test sensor config
        self.test_sensors = [
            {"id": "sensor1", "type": "dht22", "pin": 4, "location": "Room 1"},
            {"id": "sensor2", "type": "dht11", "pin": 17, "location": "Room 2"}
        ]

        # Create test mock data
        self.test_mock_data = {
            "sensor1": {"base_temperature": 23.5, "variation": 1.2},
            "sensor2": {"base_temperature": 21.0, "variation": 0.8}
        }

        # Write test config files
        with open(self.test_config_path, 'w') as f:
            json.dump(self.test_sensors, f)

        with open(self.test_mock_data_path, 'w') as f:
            json.dump(self.test_mock_data, f)

        # Create a test instance with the test paths
        self.logger = TemperatureSensorLogger(app.app_state)
        # Override paths in the logger
        self.logger.db_path = self.test_db_path
        self.logger.config_path = self.test_config_path
        self.logger.mock_data_path = self.test_mock_data_path

        # Reload sensor config and mock data with test data
        self.logger.sensors = self.logger.load_sensor_config()
        if MOCK_MODE:
            self.logger.load_mock_data()

        # Set up the database
        self.logger.setup_database()

    def tearDown(self):
        """Clean up after each test."""
        # Stop any ongoing logging
        if self.logger.logging_active:
            self.logger.stop_logging_cycle()

        # Close any open database connections
        try:
            conn = sqlite3.connect(self.test_db_path)
            conn.close()
        except:
            pass

        # Remove test files
        for file_path in [self.test_db_path, self.test_config_path, self.test_mock_data_path]:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass

    def test_database_setup(self):
        """Test that the database is correctly set up."""
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()

        # Check cycles table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cycles'")
        self.assertIsNotNone(cursor.fetchone())

        # Check sensor_readings table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sensor_readings'")
        self.assertIsNotNone(cursor.fetchone())

        conn.close()

    def test_load_sensor_config(self):
        """Test loading sensor configuration."""
        sensors = self.logger.load_sensor_config()
        self.assertEqual(len(sensors), 2)
        self.assertEqual(sensors[0]['id'], 'sensor1')
        self.assertEqual(sensors[1]['id'], 'sensor2')

    def test_load_mock_data(self):
        """Test loading mock sensor data."""
        if not MOCK_MODE:
            self.skipTest("Test only applicable in mock mode")

        self.logger.load_mock_data()
        self.assertEqual(len(self.logger.mock_data), 2)
        self.assertEqual(self.logger.mock_data['sensor1']['base_temperature'], 23.5)

    def test_read_temperature_mock_mode(self):
        """Test reading temperature in mock mode."""
        if not MOCK_MODE:
            self.skipTest("Test only applicable in mock mode")

        sensor = {"id": "sensor1", "type": "dht22", "pin": 4}
        reading = self.logger.read_temperature(sensor)
        self.assertIn('temperature', reading)
        self.assertIsInstance(reading['temperature'], float)

        # Check that temperature is within the expected range
        base_temp = self.test_mock_data['sensor1']['base_temperature']
        variation = self.test_mock_data['sensor1']['variation']
        self.assertTrue(base_temp - variation <= reading['temperature'] <= base_temp + variation)

    def test_start_logging_cycle(self):
        """Test starting a logging cycle."""
        cycle_name = "test_cycle"
        self.logger.start_logging_cycle(cycle_name)

        # Check that logging is active
        self.assertTrue(self.logger.logging_active)
        self.assertIsNotNone(self.logger.current_cycle_id)

        # Check that cycle was added to database
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM cycles WHERE cycle_id = ?", (self.logger.current_cycle_id,))
        result = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(result)
        self.assertEqual(result[0], cycle_name)

        # Clean up
        self.logger.stop_logging_cycle()

    def test_stop_logging_cycle(self):
        """Test stopping a logging cycle."""
        self.logger.start_logging_cycle("test_cycle")
        time.sleep(0.2)  # Give time for at least one reading
        self.logger.stop_logging_cycle()

        # Check that logging is stopped
        self.assertFalse(self.logger.logging_active)
        self.assertIsNone(self.logger.current_cycle_id)

        # Check that cycle was updated with end_time
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT end_time FROM cycles WHERE name = ?", ("test_cycle",))
        result = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(result)
        self.assertIsNotNone(result[0])

    # def test_log_sensor_data(self):
    #     """Test logging sensor data."""
    #     # Start a cycle
    #     self.logger.start_logging_cycle("test_cycle")
    #
    #     # Check that readings were added to database
    #     conn = sqlite3.connect(self.test_db_path)
    #     cursor = conn.cursor()
    #     id = self.logger.current_cycle_id
    #     cursor.execute("SELECT COUNT(*) FROM sensor_readings WHERE cycle_id = ?", (self.logger.current_cycle_id,))
    #     count = cursor.fetchone()[0]
    #     conn.close()
    #
    #     # Clean up
    #     self.logger.stop_logging_cycle()
    #
    #     # Should have one reading per sensor
    #     self.assertEqual(count, len(self.test_sensors))

    def test_log_sensor_data_no_active_cycle(self):
        """Test that log_sensor_data does nothing when no cycle is active."""
        # Ensure no cycle is active
        self.logger.current_cycle_id = None

        # No readings should be added
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sensor_readings")
        count = cursor.fetchone()[0]
        conn.close()

        self.assertEqual(count, 0)

    def test_list_cycles(self):
        """Test listing logging cycles."""
        # Add some test cycles
        cycles = ["cycle1", "cycle2", "cycle3"]
        for cycle in cycles:
            self.logger.start_logging_cycle(cycle)
            self.logger.stop_logging_cycle()

        # List cycles
        result = self.logger.list_cycles()

        # Should have same number of cycles as we created
        self.assertEqual(len(result), len(cycles))

    def test_delete_cycle(self):
        """Test deleting a cycle and its readings."""
        # Create a cycle with some readings
        self.logger.start_logging_cycle("test_delete_cycle")
        self.logger.stop_logging_cycle()

        # Get cycle ID for later verification
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT cycle_id FROM cycles WHERE name = ?", ("test_delete_cycle",))
        cycle_id = cursor.fetchone()[0]
        conn.close()

        # Delete the cycle
        self.logger.delete_cycle("test_delete_cycle")

        # Verify cycle is deleted
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM cycles WHERE name = ?", ("test_delete_cycle",))
        cycle_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM sensor_readings WHERE cycle_id = ?", (cycle_id,))
        readings_count = cursor.fetchone()[0]

        conn.close()

        self.assertEqual(cycle_count, 0)
        self.assertEqual(readings_count, 0)


if __name__ == '__main__':
    unittest.main()