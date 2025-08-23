import sqlite3
from contextlib import contextmanager
from typing import List, Optional, Tuple, Any, Dict
from datetime import datetime

from app.backend.Interfaces.ICalculationService import ICalculationService
from app.backend.Interfaces.ISensorReader import ISensorReader
from app.backend.Technical.Logging import LoggingMixin


class DatabaseManager(LoggingMixin):
    """Manages database operations for the climate chamber application."""

    def __init__(self, db_path: str = 'ClimateChamber_data.db', sensor_reader: Optional[ISensorReader] = None,
                 calculation_service: ICalculationService = None, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.db_path = db_path
        self.logging_active = False
        self.current_cycle_id: Optional[int] = None
        self.sensor_reader = sensor_reader
        if sensor_reader:
            sensor_reader.subscribe(self.on_sensor_data)
        self.calculation_service = calculation_service
        if calculation_service:
            calculation_service.subscribe(self.on_calculation_data)
        self.setup_database()

    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def setup_database(self) -> None:
        """Ensure the database and required tables exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS cycles (
                cycle_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                start_time TEXT,
                end_time TEXT,
                origin_page TEXT
            )
            ''')
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS sensor_readings (
                reading_id INTEGER PRIMARY KEY AUTOINCREMENT,
                sensor_type TEXT,
                cycle_id INTEGER,
                sensor_id TEXT,
                timestamp TEXT,
                value REAL,
                FOREIGN KEY (cycle_id) REFERENCES cycles (cycle_id)
            )
            ''')
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS calculation_data (
                calculation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                cycle_id INTEGER,
                calculation_name TEXT,
                timestamp TEXT,
                pid_output REAL,
                current_temp REAL,
                target_temp REAL,
                error REAL,
                control_status TEXT,
                FOREIGN KEY (cycle_id) REFERENCES cycles (cycle_id)
            )
            ''')
            
            # Add control_status column to existing tables if it doesn't exist
            try:
                cursor.execute('ALTER TABLE calculation_data ADD COLUMN control_status TEXT')
            except:
                pass  # Column already exists
                
            # Add origin_page column to cycles table if it doesn't exist
            try:
                cursor.execute('ALTER TABLE cycles ADD COLUMN origin_page TEXT')
            except:
                pass  # Column already exists
                
            conn.commit()

    def start_logging_cycle(self, cycle_name: str, origin_page: str = None) -> bool:
        """Start a new logging cycle.
        
        Args:
            cycle_name: Name of the logging cycle
            origin_page: Page where the cycle was started ('display-graph' or 'manual-control')
            
        Returns:
            bool: True if cycle started successfully, False otherwise
        """
        if self.logging_active:
            self.print("Logging cycle already in progress.")
            return False

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO cycles (name, start_time, origin_page) VALUES (?, ?, ?)",
                    (cycle_name, datetime.now().isoformat(), origin_page)
                )
                self.current_cycle_id = cursor.lastrowid
                conn.commit()
                self.logging_active = True
                self.print(f"Started logging cycle: {cycle_name} from {origin_page}")
                return True
        except Exception as e:
            self.print_error(f"Error starting logging cycle: {str(e)}")
            return False

    def on_sensor_data(self, sensor_readings: Dict[str, Dict[str, float]]) -> None:
        """Handle incoming sensor data and log it to the database.

        Args:
            sensor_readings: Dictionary mapping sensor names to {sensor_value, sensor_source}
        """
        if not self.logging_active or not self.current_cycle_id:
            self.print("No active logging cycle.")
            return
        print(f"[DatabaseManager][on_sensor_data] Received sensor data {sensor_readings}")
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                timestamp = datetime.now().isoformat()

                # Process each sensor in the new flat structure
                for sensor_name, sensor_info in sensor_readings.items():
                    # Skip cache info and invalid entries
                    if sensor_name == '_cache_info' or not isinstance(sensor_info, dict):
                        continue
                    
                    if 'sensor_value' not in sensor_info or sensor_info['sensor_value'] is None:
                        continue
                    
                    sensor_value = sensor_info['sensor_value']
                    sensor_source = sensor_info.get('sensor_source', 'unknown')
                    
                    # Determine sensor type based on known sensor names and their units
                    # You might want to get this from sensor config instead
                    if any(temp_keyword in sensor_name.lower() for temp_keyword in ['temp', 'peltier', 'outside', 'inside', 'environment']):
                        sensor_type = 'temperature'
                        unit = '°C'
                    elif 'current' in sensor_name.lower() or sensor_name.startswith(('R_IS_', 'L_IS_')):
                        sensor_type = 'current'
                        unit = 'A'
                    else:
                        # Default to temperature for DS18B20 sensors, current for ADS sensors
                        sensor_type = 'temperature'  # Default assumption
                        unit = '°C'
                    
                    # Insert sensor reading
                    cursor.execute(
                        "INSERT INTO sensor_readings (sensor_type, cycle_id, sensor_id, timestamp, value) VALUES (?, ?, ?, ?, ?)",
                        (sensor_type, self.current_cycle_id, sensor_name, timestamp, sensor_value)
                    )
                    self.print(f"[DatabaseManager] [on_sensor_data] Logged: Sensor {sensor_name}, {sensor_type}: {sensor_value}{unit} (source: {sensor_source})")

                conn.commit()
        except Exception as e:
            self.print_error(f"Error logging sensor data: {str(e)}")

    def on_calculation_data(self, calculation_readings: Dict[str, float]) -> None:
        """Handle incoming calculation data and log it to the database.

        Args:
            calculation_readings: Dictionary with keys: pid_output, current_temp, target_temp, error
        """
        if not self.logging_active or not self.current_cycle_id:
            self.print("No active logging cycle.")
            return

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                timestamp = datetime.now().isoformat()

                # Extract calculation data, handling None values properly
                pid_output = calculation_readings.get("pid_output", 0.0)
                current_temp = calculation_readings.get("current_temp")
                target_temp = calculation_readings.get("target_temp")
                error = calculation_readings.get("error")
                control_status = calculation_readings.get("status", calculation_readings.get("control_status", "UNKNOWN"))
                
                # Convert None to 0.0 for database storage to avoid NULL issues
                current_temp = current_temp if current_temp is not None else 0.0
                target_temp = target_temp if target_temp is not None else 0.0
                error = error if error is not None else 0.0

                cursor.execute(
                    "INSERT INTO calculation_data (cycle_id, calculation_name, timestamp, pid_output, current_temp, target_temp, error, control_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (self.current_cycle_id, "PID_Control", timestamp, pid_output, current_temp, target_temp, error, control_status)
                )

                self.print(
                    f"[DatabaseManager] [on_calculation_data]Logged calculation data: PID Output: {pid_output}, Current Temp: {current_temp}°C, Target Temp: {target_temp}°C, Error: {error}")
                conn.commit()

        except Exception as e:
            self.print_error(f"Error logging calculation data: {str(e)}")

    def stop_logging_cycle(self) -> bool:
        """Stop the ongoing logging cycle.
        
        Returns:
            bool: True if cycle stopped successfully, False otherwise
        """
        if not self.logging_active or not self.current_cycle_id:
            self.print("No active logging cycle to stop.")
            return False

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE cycles SET end_time = ? WHERE cycle_id = ?",
                    (datetime.now().isoformat(), self.current_cycle_id)
                )
                conn.commit()
                self.logging_active = False
                self.current_cycle_id = None
                self.print("Logging cycle stopped.")
                return True
        except Exception as e:
            self.print_error(f"Error stopping logging cycle: {str(e)}")
            return False

    def delete_cycle(self, cycle_name: str) -> bool:
        """Delete a cycle and its associated sensor data from the database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT cycle_id FROM cycles WHERE name = ?", (cycle_name,))
            cycle = cursor.fetchone()
            
            if not cycle:
                self.print(f"Cycle '{cycle_name}' not found.")
                return False

            cycle_id = cycle[0]
            cursor.execute("DELETE FROM sensor_readings WHERE cycle_id = ?", (cycle_id,))
            cursor.execute("DELETE FROM calculation_data WHERE cycle_id = ?", (cycle_id,))
            cursor.execute("DELETE FROM cycles WHERE cycle_id = ?", (cycle_id,))
            conn.commit()
            self.print(f"Deleted cycle '{cycle_name}' and associated sensor readings.")
            return True

        def delete_cycle(self, cycle_name: str) -> bool:
            """Delete a cycle and its associated sensor data from the database."""
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT cycle_id FROM cycles WHERE name = ?", (cycle_name,))
                cycle = cursor.fetchone()

                if not cycle:
                    self.print(f"Cycle '{cycle_name}' not found.")
                    return False

                cycle_id = cycle[0]
                cursor.execute("DELETE FROM sensor_readings WHERE cycle_id = ?", (cycle_id,))
                cursor.execute("DELETE FROM calculation_data WHERE cycle_id = ?", (cycle_id,))
                cursor.execute("DELETE FROM cycles WHERE cycle_id = ?", (cycle_id,))
                conn.commit()
                self.print(f"Deleted cycle '{cycle_name}' and associated sensor readings.")
                return True

    def delete_all_cycles(self) -> bool:
        """Delete all cycles and their associated sensor and calculation data from the database."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Get all cycle IDs first
                cursor.execute("SELECT cycle_id, name FROM cycles")
                all_cycles = cursor.fetchall()

                if not all_cycles:
                    self.print("No cycles found to delete.")
                    return True

                # Delete all data in correct order (foreign key constraints)
                cursor.execute("DELETE FROM sensor_readings")
                cursor.execute("DELETE FROM calculation_data")
                cursor.execute("DELETE FROM cycles")

                conn.commit()

                self.print(f"Deleted {len(all_cycles)} cycles and all associated data.")
                for cycle_id, cycle_name in all_cycles:
                    self.print(f"  - Deleted cycle: '{cycle_name}'")

                return True

        except Exception as e:
            self.print_error(f"Error deleting all cycles: {str(e)}")
            return False

    def list_cycles(self) -> List[Tuple[Any, ...]]:
        """Retrieve a list of all logging cycles."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM cycles")
            return cursor.fetchall()

    def list_cycle_names(self) -> List[Tuple[str, ...]]:
        """Retrieve a list of all cycle names."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM cycles")
            return cursor.fetchall()

    def read_cycle_data(self, cycle_name: str) -> Dict[str, List[Tuple]]:
        """Read all sensor data and calculation data for a specific cycle.

        Args:
            cycle_name: Name of the cycle to read data for

        Returns:
            Dict containing 'sensor_data' and 'calculation_data' lists
            sensor_data: List of tuples (sensor_id, timestamp, temperature)
            calculation_data: List of tuples (calculation_name, timestamp, pid_output, current_temp, target_temp, error)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT cycle_id FROM cycles WHERE name = ?", (cycle_name,))
            cycle = cursor.fetchone()

            if not cycle:
                return {"sensor_data": [], "calculation_data": []}

            cycle_id = cycle[0]

            # Get sensor data
            cursor.execute(
                "SELECT sensor_id, timestamp, value FROM sensor_readings WHERE cycle_id = ? and sensor_type = ?",
                (cycle_id, 'temperature')
            )
            sensor_temperature_data = cursor.fetchall()

            cursor.execute(
                "SELECT sensor_id, timestamp, value FROM sensor_readings WHERE cycle_id = ? and sensor_type = ?",
                (cycle_id, 'current')
            )
            sensor_current_data = cursor.fetchall()

            sensor_data = {'temperature': [sensor_temperature_data], 'current': [sensor_current_data]}

            # Get calculation data
            cursor.execute(
                "SELECT calculation_name, timestamp, pid_output, current_temp, target_temp, error, control_status FROM calculation_data WHERE cycle_id = ?",
                (cycle_id,)
            )
            calculation_data = cursor.fetchall()

            return {
                "sensor_data": sensor_data,
                "calculation_data": calculation_data
            }