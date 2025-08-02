
import threading
import time
from datetime import datetime

from app.backend.Dataclasses.Config import McuConfig
from app.backend.Interfaces.ISensorReader import ISensorReader
from app.backend.Sensors.ADS1115 import ADS1115
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
                        if isinstance(sensor, DS18B20Cluster) and sensor.group_name == sensor_config.group_name:
                            existing_cluster = sensor
                            break
                    if existing_cluster:
                        existing_cluster.append(sensor_config)
                    else:
                        self.sensor_list.append(DS18B20Cluster(sensor_config))
                elif sensor_config.type == "ADS1115":
                    self.sensor_list.append(ADS1115(sensor_config))
                elif sensor_config.type == "MPL3115A2":
                    self.sensor_list.append(MPL3115A2(sensor_config.name, sensor_config.SDA,sensor_config.SCL, sensor_config.min_value, sensor_config.max_value, sensor_config.unit))
        except Exception as e:
            raise RuntimeError(f"Configuration error: {str(e)}")

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
                        print(f"[SensorReader] Returning cached data (age: {age:.1f}s)")
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
                        print(f"[SensorReader] Cached data too old ({age:.1f}s), falling back to direct read")
        
        # Fallback: direct read if background reading not active or no cached data
        if not background_running:
            print("[SensorReader] Background reading not active, reading sensors directly")
        else:
            print("[SensorReader] No cached data available, reading sensors directly")
            
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
            print("[SensorReader] Background reading already running")
            return
        
        self._stop_background = False
        self._background_thread = threading.Thread(target=self._background_read_loop, daemon=True)
        self._background_thread.start()
        print(f"[SensorReader] Background reading started (interval: {self._reading_interval}s)")
    
    def stop_background_reading(self):
        """Stop the background sensor reading thread."""
        if self._background_thread:
            self._stop_background = True
            self._background_thread.join(timeout=5.0)
            print("[SensorReader] Background reading stopped")
    
    def _background_read_loop(self):
        """Continuously read sensors in background and store values."""
        print("[SensorReader] Background reading loop started")
        
        while not self._stop_background:
            try:
                # Read all sensors
                fresh_data = self._read_sensors_directly()
                
                # Store the data with thread safety
                with self._data_lock:
                    self._cached_sensor_data = fresh_data
                    self._last_reading_time = datetime.now()
                
                print(f"[SensorReader] Background read complete at {self._last_reading_time}")
                
            except Exception as e:
                print(f"[SensorReader] Error in background reading: {e}")
            
            # Wait before next reading
            time.sleep(self._reading_interval)
        
        print("[SensorReader] Background reading loop ended")
    
    def _read_sensors_directly(self):
        """Read sensors directly (used by background thread)."""
        sensor_readings = {}
        for sensor in self.sensor_list:
            try:
                reading = sensor.read()  # e.g., {'sensor_name': {'sensor_value': 19.9, 'sensor_source': 'real'}}
                
                # Merge sensor readings directly into the main dict
                sensor_readings.update(reading)
                    
            except Exception as e:
                print(f"[SensorReader] Error reading sensor {getattr(sensor, 'name', 'unknown')}: {e}")
        
        return sensor_readings
    
    def set_peltier_enabled(self, enabled: bool):
        """Set whether peltier modules are enabled.
        
        Args:
            enabled: True if peltier modules are enabled, False otherwise
        """
        with self._peltier_state_lock:
            self._peltier_enabled = enabled
            print(f"[SensorReader] Peltier enabled state set to: {enabled}")
    
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
                        print(f"[SensorReader] Overrode {sensor_name} to 0A (peltier disabled)")
                
                return corrected_readings
            
            return sensor_readings
    
    def __del__(self):
        """Cleanup background thread when SensorReader is destroyed."""
        self.stop_background_reading()