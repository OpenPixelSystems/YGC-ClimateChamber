import sqlite3
import json
import time
import threading
import random
from datetime import datetime

# Mock imports for testing
class MockGPIO:
    BOARD = 1
    BCM = 2
    IN = 3
    OUT = 4

    @staticmethod
    def setmode(mode):
        pass

    @staticmethod
    def setup(pin, mode):
        pass

    @staticmethod
    def cleanup():
        pass


class MockDHT:
    DHT11 = 1
    DHT22 = 2

    @staticmethod
    def read_retry(sensor_type, pin):
        return None, None


try:
    import RPi.GPIO as GPIO
    import Adafruit_DHT

    MOCK_MODE = False
    print("Running with real GPIO libraries")
except ImportError:
    GPIO = MockGPIO()
    Adafruit_DHT = MockDHT()
    MOCK_MODE = True
    print("Running in mock mode (no GPIO libraries found)")


class DatabaseManager:
    def __init__(self, db_path='ClimateChamber_data.db'):
        self.db_path = db_path
        self.setup_database()

    def setup_database(self):
        """Ensure the database and required tables exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS cycles (
            cycle_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            start_time TEXT,
            end_time TEXT
        )
        ''')
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sensor_readings (
            reading_id INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle_id INTEGER,
            sensor_id TEXT,
            timestamp TEXT,
            temperature REAL,
            FOREIGN KEY (cycle_id) REFERENCES cycles (cycle_id)
        )
        ''')
        conn.commit()
        conn.close()

    def delete_cycle(self, cycle_name):
        """Delete a cycle and its associated sensor data from the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT cycle_id FROM cycles WHERE name = ?", (cycle_name,))
        cycle = cursor.fetchone()
        if cycle:
            cycle_id = cycle[0]
            cursor.execute("DELETE FROM sensor_readings WHERE cycle_id = ?", (cycle_id,))
            cursor.execute("DELETE FROM cycles WHERE cycle_id = ?", (cycle_id,))
            conn.commit()
            print(f"Deleted cycle '{cycle_name}' and associated sensor readings.")
        else:
            print(f"Cycle '{cycle_name}' not found.")
        conn.close()

    def list_cycles(self):
        """Retrieve a list of all logging cycles."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cycles")
        cycles = cursor.fetchall()
        conn.close()
        return cycles


class SensorReader:
    def __init__(self, config_path='database/sensorConfig.json', mock_data_path='database/mockSensorData.json'):
        self.config_path = config_path
        self.mock_data_path = mock_data_path
        self.sensors = self.load_sensor_config()
        self.mock_data = {}
        if MOCK_MODE:
            self.load_mock_data()

    def load_mock_data(self):
        try:
            with open(self.mock_data_path, 'r') as f:
                self.mock_data = json.load(f)
                print(f"Loaded mock data for {len(self.mock_data)} sensors")
        except (FileNotFoundError, json.JSONDecodeError):
            self.mock_data = {}

    def load_sensor_config(self):
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def read_sensors(self):
        temperatures = {}

        for sensor in self.sensors:
            sensor_id = sensor.get("id")
            if not sensor_id:
                print(f"Warning: Sensor missing ID, skipping: {sensor}")
                continue

            temperatures[f"{sensor_id}"] = self.read_temperature(sensor)['temperature']

        return temperatures

    def read_temperature(self, sensor):
        if MOCK_MODE:
            return self.read_mock_temperature(sensor)
        else:
            return self.read_real_temperature(sensor)

    def read_mock_temperature(self, sensor):
        sensor_id = sensor.get('id')
        base_temp = self.mock_data.get(sensor_id, {}).get('base_temperature', 22.0)
        variation = self.mock_data.get(sensor_id, {}).get('variation', 5.0)
        temperature = base_temp + (random.random() * 2 - 1) * variation
        return {'temperature': round(temperature, 2)}

    def read_real_temperature(self, sensor):
        sensor_type = sensor.get('type', '').lower()
        sensor_pin = sensor.get('pin')
        if sensor_type in ['dht22', 'dht11']:
            model = Adafruit_DHT.DHT22 if sensor_type == 'dht22' else Adafruit_DHT.DHT11
            humidity, temperature = Adafruit_DHT.read_retry(model, sensor_pin)
            return {'temperature': temperature, 'humidity': humidity if humidity is not None else 0}
        return None


class TemperatureSensorLogger(DatabaseManager, SensorReader):
    def __init__(self, app_state):
        self.app_state = app_state
        DatabaseManager.__init__(self)
        SensorReader.__init__(self)
        self.logging_active = False
        self.logging_thread = None
        self.current_cycle_id = None

    """ Periodically read connected sensor and write data to database. """
    def start_logging_cycle(self, cycle_name):
        """Start an asynchronous logging cycle."""
        if self.logging_active:
            print("Logging cycle already in progress.")
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO cycles (name, start_time) VALUES (?, ?)", (cycle_name, datetime.now().isoformat()))
        self.current_cycle_id = cursor.lastrowid
        conn.commit()
        conn.close()

        self.logging_active = True
        self.logging_thread = threading.Thread(target=self.__logging_loop, args=(self.app_state.provider_interval,), daemon=True)
        self.logging_thread.start()
        print(f"Started logging cycle: {cycle_name}")

    def __logging_loop(self, interval):
        """Background process for logging sensor data at a set interval."""
        while self.logging_active:
            self.__log_sensor_data()
            time.sleep(interval)

    def __log_sensor_data(self):
        """Read temperature data from all configured sensors and log to the database."""
        if not self.current_cycle_id:
            print("No active logging cycle.")
            return

        timestamp = datetime.now().isoformat()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for sensor in self.sensors:
            sensor_id = sensor.get('id')
            if not sensor_id:
                print(f"Warning: Sensor missing ID, skipping: {sensor}")
                continue

            reading = self.read_temperature(sensor)
            if reading and 'temperature' in reading:
                temperature = reading['temperature']
                if temperature is not None:
                    cursor.execute(
                        "INSERT INTO sensor_readings (cycle_id, sensor_id, timestamp, temperature) VALUES (?, ?, ?, ?)",
                        (self.current_cycle_id, sensor_id, timestamp, temperature)
                    )
                    print(f"Logged: Sensor {sensor_id}, Temperature: {temperature}°C, Time: {timestamp}")
                else:
                    print(f"Warning: Null temperature reading from sensor {sensor_id}")
            else:
                print(f"Warning: Failed to get reading from sensor {sensor_id}")

        conn.commit()
        conn.close()

    def stop_logging_cycle(self):
        """Stop the ongoing logging cycle."""
        self.logging_active = False
        if self.logging_thread:
            self.logging_thread.join()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE cycles SET end_time = ? WHERE cycle_id = ?",
                       (datetime.now().isoformat(), self.current_cycle_id))
        conn.commit()
        conn.close()
        print("Logging cycle stopped.")
        self.current_cycle_id = None
