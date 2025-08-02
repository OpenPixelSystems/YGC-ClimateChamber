#!/usr/bin/env python3
"""
Current Sensor Calibration Script
Run this on the Raspberry Pi to calibrate ADS1115 current sensors.

Usage:
1. Connect multimeter to measure actual current
2. Run this script
3. Enter the actual current reading when prompted
4. Script will calculate correct calibration values
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.backend.Dataclasses.Config import McuConfig, ADS1115Config
from app.backend.Sensors.ADS1115 import ADS1115

def find_current_sensors_in_config():
    """Find all current sensors in the configuration."""
    try:
        # Try to load the actual config
        from app.backend.Implementations.ConfigManager import ConfigManager
        config_manager = ConfigManager()
        mcu_config = config_manager.mcu_config
        
        current_sensors = []
        for sensor_config in mcu_config.sensors:
            if sensor_config.type == "ADS1115":
                # Create ADS1115 instance
                current_sensors.append(sensor_config)
        
        return current_sensors
    except Exception as e:
        print(f"Could not load config: {e}")
        return []

def calibrate_single_sensor(sensor_config):
    """Calibrate a single current sensor."""
    print(f"\n=== Calibrating {sensor_config.name} ===")
    
    # Create sensor instance
    sensor = ADS1115(sensor_config)
    
    # Read current values
    print("Reading current sensor values...")
    readings = sensor.read()
    
    if sensor_config.name in readings:
        sensor_data = readings[sensor_config.name]
        if sensor_data['sensor_value'] is not None:
            ads_reading = sensor_data['sensor_value']
            print(f"ADS1115 reading: {ads_reading:.3f} {sensor_config.unit}")
            
            # Get actual current from user
            try:
                actual_current = float(input(f"Enter actual current measured with multimeter (in A): "))
                
                # Run calibration
                if hasattr(sensor, 'calibrate_current_sensor'):
                    calculated_sensitivity = sensor.calibrate_current_sensor(actual_current)
                    
                    print(f"\nTo fix the calibration, update the ADS1115.py file:")
                    print(f"Change line ~45: self._sensitivity = {calculated_sensitivity:.3f}  # Was {sensor._sensitivity:.3f}")
                    
                    return calculated_sensitivity
                else:
                    print("Calibration method not available")
            except ValueError:
                print("Invalid input, skipping this sensor")
        else:
            print(f"Could not read from sensor {sensor_config.name}")
    else:
        print(f"Sensor {sensor_config.name} not found in readings")
    
    return None

def main():
    """Main calibration routine."""
    print("=== ADS1115 Current Sensor Calibration ===")
    print("Make sure your peltier is running and drawing current!")
    print("Have a multimeter ready to measure actual current.")
    print()
    
    # Find current sensors
    current_sensors = find_current_sensors_in_config()
    
    if not current_sensors:
        print("No ADS1115 current sensors found in configuration.")
        print("Creating test configuration...")
        
        # Create a test config
        test_config = ADS1115Config(
            name="test_current_sensor",
            type="ADS1115", 
            SDA=2,
            SCL=3,
            read_pin=0,
            min_value=0.0,
            max_value=10.0,
            unit="A",
            voltage_offset=0.0
        )
        current_sensors = [test_config]
    
    print(f"Found {len(current_sensors)} current sensor(s)")
    
    # Calibrate each sensor
    calibration_results = {}
    for sensor_config in current_sensors:
        try:
            result = calibrate_single_sensor(sensor_config)
            if result is not None:
                calibration_results[sensor_config.name] = result
        except Exception as e:
            print(f"Error calibrating {sensor_config.name}: {e}")
    
    # Summary
    if calibration_results:
        print(f"\n=== CALIBRATION SUMMARY ===")
        print("Update ADS1115.py with these values:")
        for sensor_name, sensitivity in calibration_results.items():
            print(f"  {sensor_name}: self._sensitivity = {sensitivity:.3f}")
        print(f"\nAfter updating, restart your application to use the new calibration.")
    else:
        print("\nNo successful calibrations completed.")

if __name__ == "__main__":
    main()