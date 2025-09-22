
import threading
import time
from datetime import datetime

from app.backend.Dataclasses.Config import McuConfig
from app.backend.Interfaces.ISensorReader import ISensorReader
from app.backend.Sensors.ADS1115 import ADS1115
from app.backend.Sensors.NTCTemperatureSensor import NTCTemperatureSensor
from app.backend.Sensors.DS18B20 import DS18B20
from app.backend.Sensors.DS18B20Cluster import DS18B20Cluster
from app.backend.Sensors.MPL3115A2 import MPL3115A2
from app.backend.Services.Subscribe import Subscriptable


class SensorReader(ISensorReader, Subscriptable):
    """Handles initialisation, reading and logging logic of all connected Sensors """
    #TODO add reload functionality for when config file gets edited

    def __init__(self, mcu_config: McuConfig):
        super().__init__()
        self.sensor_list = []
        self.inside_sensors_list = []
        
        # Background reading setup
        self._cached_sensor_data = {}
        self._last_reading_time = None
        self._data_lock = threading.Lock()
        self._background_thread = None
        self._stop_background = False
        self._reading_interval = 1.0  # Read sensors every 1 second
        
        # Peltier state tracking
        self._peltier_enabled = False  # Default to enabled
        self._peltier_state_lock = threading.Lock()
        
        self.initialise(mcu_config)
        self.set_inside_sensors()
        
        # Background reading will be started manually when needed (when cycle starts)

    def initialise(self, mcu_config: McuConfig):
        """Initialize Sensors from McuConfig dataclass"""
        try:
            # Iterate through all Sensors in the config
            for sensor_config in mcu_config.sensors:
                # Create the appropriate sensor instance
                if sensor_config.type == "DS18B20":
                    existing_cluster = None
                    for sensor in self.sensor_list:
                        if isinstance(sensor, DS18B20Cluster) and sensor.sensor_location == sensor_config.sensor_location:
                            existing_cluster = sensor
                            break
                    if existing_cluster:
                        existing_cluster.append(sensor_config)
                    else:
                        self.sensor_list.append(DS18B20Cluster(sensor_config))
                elif sensor_config.type == "ADS1115":
                    self.sensor_list.append(ADS1115(sensor_config))
                elif sensor_config.type == "NTC":
                    self.sensor_list.append(NTCTemperatureSensor(sensor_config))
                elif sensor_config.type == "MPL3115A2":
                    self.sensor_list.append(MPL3115A2(sensor_config.name, sensor_config.SDA,sensor_config.SCL, sensor_config.min_value, sensor_config.max_value, sensor_config.unit))
        except Exception as e:
            raise RuntimeError(f"Configuration error: {str(e)}")

    def set_inside_sensors(self):
        for sensor in self.sensor_list:
            if (sensor.type == 'NTC') and sensor.sensor_location == "Inside":
                self.inside_sensors_list.append(sensor)

    def read_inside_sensors(self):
        # Reading inside sensors for temperature average
        temperature_readings = []
        for sensor in self.inside_sensors_list:
            try:
                reading = sensor.read()  # e.g., {'sensor_name': {'sensor_value': 19.9, 'sensor_source': 'real'}}

                # Extract sensor values from the reading dictionary
                for sensor_name, sensor_data in reading.items():
                    if isinstance(sensor_data, dict) and 'sensor_value' in sensor_data:
                        temperature_readings.append(sensor_data['sensor_value'])
            except Exception as e:
                self.print_error(f"Error reading sensor {getattr(sensor, 'name', 'unknown')}: {e}")

        return sum(temperature_readings) / len(temperature_readings)

    """Return cached sensor values without notifications - for streaming only"""
    def read_sensors_no_notify(self):
        # Check if background reading is running
        background_running = self._background_thread and self._background_thread.is_alive()

        # Try to return cached data first (instant response) - only if background reading is active
        if background_running:
            with self._data_lock:
                if self._cached_sensor_data and self._last_reading_time:
                    age = (datetime.now() - self._last_reading_time).total_seconds()
                    if age < 10.0:  # Use cache if less than 10 seconds old
                        # Return cached data for streaming
                        cached_data = self._cached_sensor_data.copy()
                        # Add cache metadata to indicate this is cached data
                        cache_status = 'cached_recent' if age < 3.0 else 'cached_old'
                        cached_data['_cache_info'] = {
                            'source': cache_status,
                            'age_seconds': round(age, 1),
                            'cached_at': self._last_reading_time.isoformat(),
                            'is_recent': age < 3.0
                        }
                        # Apply peltier state correction to cached data
                        cached_data = self._apply_peltier_state_correction(cached_data)
                        # NO NOTIFICATION - this prevents duplicate calculations
                        return cached_data
                    else:
                        # Cached data too old for streaming
                        return {}

        # If no background reading or no cache, return empty dict for streaming
        # No cached data available for streaming
        return {}

    """Return cached sensor values (instant response) or direct read if no cache available"""
    def read_sensors(self):
        # Check if background reading is running
        background_running = self._background_thread and self._background_thread.is_alive()
        
        # Try to return cached data first (instant response) - only if background reading is active
        if background_running:
            with self._data_lock:
                if self._cached_sensor_data and self._last_reading_time:
                    age = (datetime.now() - self._last_reading_time).total_seconds()
                    if age < 10.0:  # Use cache if less than 10 seconds old
                        # Return cached sensor data
                        cached_data = self._cached_sensor_data.copy()
                        # Add cache metadata to indicate this is cached data
                        # Determine if cache is recent (< 3 seconds) or old
                        cache_status = 'cached_recent' if age < 3.0 else 'cached_old'
                        cached_data['_cache_info'] = {
                            'source': cache_status,
                            'age_seconds': round(age, 1),
                            'cached_at': self._last_reading_time.isoformat(),
                            'is_recent': age < 3.0
                        }
                        # Apply peltier state correction to cached data
                        cached_data = self._apply_peltier_state_correction(cached_data)
                        self.notify(cached_data)
                        return cached_data
                    else:
                        # Cached data too old, reading sensors directly
        
        # Fallback: direct read if background reading not active or no cached data
        if not background_running:
            # Background reading not active, read sensors directly
        else:
            # No cached data available, read sensors directly
            
        sensor_readings = self._read_sensors_directly()
        
        # Add direct read metadata
        sensor_readings['_cache_info'] = {
            'source': 'direct',
            'read_at': datetime.now().isoformat()
        }
        
        # Apply peltier state correction to direct readings
        sensor_readings = self._apply_peltier_state_correction(sensor_readings)
        
        self.notify(sensor_readings)
        return sensor_readings

    def subscribe(self, callback):
        Subscriptable.subscribe(self,callback)

    def start_background_reading(self):
        """Start the background sensor reading thread."""
        if self._background_thread and self._background_thread.is_alive():
            return  # Background reading already running
            return
        
        self._stop_background = False
        self._background_thread = threading.Thread(target=self._background_read_loop, daemon=True)
        self._background_thread.start()
        self.print(f"[SensorReader] Background reading started (interval: {self._reading_interval}s)")
    
    def stop_background_reading(self):
        """Stop the background sensor reading thread."""
        if self._background_thread:
            self._stop_background = True
            self._background_thread.join(timeout=5.0)
            self.print("[SensorReader] Background reading stopped")
    
    def _background_read_loop(self):
        """Continuously read sensors in background and store values."""
        # Background reading loop started
        
        while not self._stop_background:
            try:
                # Read all sensors
                fresh_data = self._read_sensors_directly()
                
                # Store the data with thread safety
                with self._data_lock:
                    self._cached_sensor_data = fresh_data
                    self._last_reading_time = datetime.now()
                
                # Apply peltier state correction and notify subscribers
                corrected_data = self._apply_peltier_state_correction(fresh_data)
                self.notify(corrected_data)
                
                # Background read complete
                
            except Exception as e:
                self.print_error(f"[SensorReader] Error in background reading: {e}")
            
            # Wait before next reading
            time.sleep(self._reading_interval)
        
        self.print("[SensorReader] Background reading loop ended")
    
    def _read_sensors_directly(self):
        """Read sensors directly (used by background thread)."""
        sensor_readings = {}
        for sensor in self.sensor_list:
            try:
                reading = sensor.read()  # e.g., {'sensor_name': {'sensor_value': 19.9, 'sensor_source': 'real'}}
                
                # Merge sensor readings directly into the main dict
                sensor_readings.update(reading)
                    
            except Exception as e:
                self.print_error(f"Error reading sensor {getattr(sensor, 'name', 'unknown')}: {e}")
        
        return sensor_readings
    
    def set_peltier_enabled(self, enabled: bool):
        """Set whether peltier modules are enabled.
        
        Args:
            enabled: True if peltier modules are enabled, False otherwise
        """
        with self._peltier_state_lock:
            self._peltier_enabled = enabled
            # Peltier enabled state updated
    
    def _is_current_sensor(self, sensor_name: str) -> bool:
        """Determine if a sensor measures current based on its name.
        
        Args:
            sensor_name: The name of the sensor
            
        Returns:
            True if the sensor measures current, False otherwise
        """
        sensor_name_lower = sensor_name.lower()
        return 'current' in sensor_name_lower or 'amp' in sensor_name_lower or sensor_name_lower.endswith('_a')
    
    def _apply_peltier_state_correction(self, sensor_readings: dict) -> dict:
        """Apply peltier state correction to sensor readings.
        
        When peltier is disabled, current sensors should read 0A as no current flows.
        
        Args:
            sensor_readings: Raw sensor readings
            
        Returns:
            Corrected sensor readings
        """
        with self._peltier_state_lock:
            if not self._peltier_enabled:
                corrected_readings = sensor_readings.copy()
                
                for sensor_name, sensor_data in sensor_readings.items():
                    # Skip metadata entries
                    if sensor_name.startswith('_'):
                        continue
                        
                    # Check if this is a current sensor and has valid data structure
                    if (isinstance(sensor_data, dict) and 
                        'sensor_value' in sensor_data and 
                        'sensor_source' in sensor_data and
                        self._is_current_sensor(sensor_name)):
                        
                        # Override current reading to 0 when peltier is disabled
                        corrected_readings[sensor_name] = {
                            'sensor_value': 0.0,
                            'sensor_source': 'peltier_disabled'
                        }
                        # Override current sensor to 0A when peltier disabled
                
                return corrected_readings
            
            return sensor_readings
    
    def get_starting_temperature(self):
        """Get the average temperature of all Inside temperature sensors (NTC and DS18B20).
        
        Returns:
            float: Average temperature of all viable temperature sensors, or None if no sensors available
        """
        try:
            # Read current sensor data
            sensor_data = self.read_sensors()
            
            # Collect temperature values from Inside sensors
            temperature_values = []
            
            for sensor_name, sensor_info in sensor_data.items():
                # Skip metadata entries
                if sensor_name.startswith('_'):
                    continue
                    
                # Check if sensor data is valid
                if not isinstance(sensor_info, dict) or 'sensor_value' not in sensor_info:
                    continue
                    
                sensor_value = sensor_info['sensor_value']
                if sensor_value is None:
                    continue
                
                # Find the sensor configuration to check type and location
                for sensor in self.sensor_list:
                    sensor_names = []
                    
                    # Handle different sensor types
                    if hasattr(sensor, 'name'):
                        sensor_names.append(sensor.name)
                    elif hasattr(sensor, 'sensors'):  # DS18B20Cluster
                        sensor_names.extend([s.name for s in sensor.sensors])
                    
                    if sensor_name in sensor_names:
                        # Check if it's a temperature sensor located Inside
                        if hasattr(sensor, 'sensor_location') and sensor.sensor_location == "Inside":
                            # Check if it's NTC or DS18B20
                            if hasattr(sensor, 'type') and sensor.type in ['NTC', 'DS18B20']:
                                temperature_values.append(sensor_value)
                                break
                        elif hasattr(sensor, 'sensors'):  # DS18B20Cluster case
                            for sub_sensor in sensor.sensors:
                                if sub_sensor.name == sensor_name and sub_sensor.sensor_location == "Inside":
                                    temperature_values.append(sensor_value)
                                    break
                            break
            
            # Return average if we have temperature values
            if temperature_values:
                average_temp = sum(temperature_values) / len(temperature_values)
                self.print(f"[SensorReader] Starting temperature: {average_temp:.1f}°C")
                return average_temp
            else:
                self.print_error("[SensorReader] No viable inside temperature sensors found")
                return None
                
        except Exception as e:
            self.print_error(f"[SensorReader] Error getting starting temperature: {e}")
            return None

    def __del__(self):
        """Cleanup background thread when SensorReader is destroyed."""
        self.stop_background_reading()