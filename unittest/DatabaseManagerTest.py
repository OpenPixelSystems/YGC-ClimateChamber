import unittest
from unittest.mock import Mock
import os
import tempfile

from app.backend.Implementations.DatabaseManager import DatabaseManager
from app.backend.Interfaces.ISensorReader import ISensorReader


class TestDatabaseManager(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a temporary database file for testing
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test_climate_chamber.db')
        
        # Create mock sensor reader
        self.mock_sensor_reader = Mock(spec=ISensorReader)
        
        # Initialize DatabaseManager with test database
        self.db_manager = DatabaseManager(
            db_path=self.db_path,
            sensor_reader=self.mock_sensor_reader
        )

    def tearDown(self):
        """Clean up after each test."""
        # Remove the temporary database file
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_initialization(self):
        """Test if DatabaseManager initializes correctly."""
        self.assertIsNotNone(self.db_manager)
        self.assertEqual(self.db_manager.db_path, self.db_path)
        self.assertFalse(self.db_manager.logging_active)
        self.assertIsNone(self.db_manager.current_cycle_id)
        self.assertEqual(self.db_manager.sensor_reader, self.mock_sensor_reader)

    def test_start_logging_cycle(self):
        """Test starting a logging cycle."""
        # Start a logging cycle
        result = self.db_manager.start_logging_cycle("test_cycle")
        self.assertTrue(result)
        self.assertTrue(self.db_manager.logging_active)
        self.assertIsNotNone(self.db_manager.current_cycle_id)

        # Try to start another cycle while one is active
        result = self.db_manager.start_logging_cycle("another_cycle")
        self.assertFalse(result)

    def test_stop_logging_cycle(self):
        """Test stopping a logging cycle."""
        # Start a cycle
        self.db_manager.start_logging_cycle("test_cycle")
        cycle_id = self.db_manager.current_cycle_id

        # Stop the cycle
        result = self.db_manager.stop_logging_cycle()
        self.assertTrue(result)
        self.assertFalse(self.db_manager.logging_active)
        self.assertIsNone(self.db_manager.current_cycle_id)

        # Verify cycle end time was set
        cycles = self.db_manager.list_cycles()
        self.assertEqual(len(cycles), 1)
        self.assertIsNotNone(cycles[0][3])  # end_time should not be None

    def test_on_sensor_data(self):
        """Test handling of sensor data."""
        # Start a logging cycle
        self.db_manager.start_logging_cycle("test_cycle")

        # Simulate sensor readings
        sensor_readings = {
            "Temp_sensor_1": 25.5,
            "Temp_sensor_2": 30.0
        }
        self.db_manager.on_sensor_data(sensor_readings)

        # Verify readings were stored
        cycle_data = self.db_manager.read_cycle_data("test_cycle")
        self.assertEqual(len(cycle_data), 2)
        
        # Verify temperature values
        temperatures = {reading[0]: reading[2] for reading in cycle_data}
        self.assertEqual(temperatures["Temp_sensor_1"], 25.5)
        self.assertEqual(temperatures["Temp_sensor_2"], 30.0)

    def test_delete_cycle(self):
        """Test deleting a cycle and its data."""
        # Create a cycle with some data
        self.db_manager.start_logging_cycle("test_cycle")
        self.db_manager.on_sensor_data({"Temp_sensor_1": 25.5})
        self.db_manager.stop_logging_cycle()

        # Delete the cycle
        result = self.db_manager.delete_cycle("test_cycle")
        self.assertTrue(result)

        # Verify cycle and its data are gone
        cycles = self.db_manager.list_cycles()
        self.assertEqual(len(cycles), 0)

    def test_list_cycles(self):
        """Test listing cycles."""
        # Create multiple cycles
        self.db_manager.start_logging_cycle("cycle1")
        self.db_manager.stop_logging_cycle()
        self.db_manager.start_logging_cycle("cycle2")
        self.db_manager.stop_logging_cycle()

        # Test list_cycles
        cycles = self.db_manager.list_cycles()
        self.assertEqual(len(cycles), 2)
        cycle_names = [cycle[1] for cycle in cycles]  # name is second column
        self.assertIn("cycle1", cycle_names)
        self.assertIn("cycle2", cycle_names)

        # Test list_cycle_names
        cycle_names = self.db_manager.list_cycle_names()
        self.assertEqual(len(cycle_names), 2)
        self.assertIn(("cycle1",), cycle_names)
        self.assertIn(("cycle2",), cycle_names)

    def test_read_cycle_data(self):
        """Test reading cycle data."""
        # Create a cycle with multiple readings
        self.db_manager.start_logging_cycle("test_cycle")
        self.db_manager.on_sensor_data({"Temp_sensor_1": 25.5})
        self.db_manager.on_sensor_data({"Temp_sensor_1": 26.0})
        self.db_manager.stop_logging_cycle()

        # Read the data
        data = self.db_manager.read_cycle_data("test_cycle")
        self.assertEqual(len(data), 2)
        
        # Verify data format
        for reading in data:
            self.assertEqual(len(reading), 3)  # sensor_id, timestamp, temperature
            self.assertEqual(reading[0], "Temp_sensor_1")
            self.assertIsInstance(reading[1], str)  # timestamp
            self.assertIsInstance(reading[2], float)  # temperature

    def test_read_nonexistent_cycle(self):
        """Test reading data from a nonexistent cycle."""
        data = self.db_manager.read_cycle_data("nonexistent_cycle")
        self.assertEqual(data, [])

    def test_delete_nonexistent_cycle(self):
        """Test deleting a nonexistent cycle."""
        result = self.db_manager.delete_cycle("nonexistent_cycle")
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main() 