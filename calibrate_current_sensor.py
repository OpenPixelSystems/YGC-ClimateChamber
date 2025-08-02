#!/usr/bin/env python3
"""
Current Sensor Calibration Script
Run this on the Raspberry Pi to calibrate ADS1115 current sensors.

Usage:
1. Connect multimeter to measure actual current
2. Run this script
3. Script will enable peltier and test at different duty cycles
4. Enter the actual current reading when prompted
5. Script will calculate correct calibration values
"""

import sys
import os
import time
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.backend.Dataclasses.Config import McuConfig, ADS1115Config
from app.backend.Sensors.ADS1115 import ADS1115

def setup_peltier_control():
    """Setup peltier control for testing."""
    try:
        from app.backend.Implementations.ConfigManager import ConfigManager
        from app.backend.Implementations.ClimateChamber import ClimateChamber
        from app.backend.Implementations.SensorReader import SensorReader
        from app.backend.Implementations.CalculationService import CalculationService
        from app.backend.Implementations.FanController import FanController
        
        # Initialize components
        config_manager = ConfigManager()
        sensor_reader = SensorReader(config_manager.mcu_config)
        calculation_service = CalculationService(config_manager.control_config)
        fan_controller = FanController(config_manager.mcu_config)
        
        climate_chamber = ClimateChamber(
            sensor_reader=sensor_reader,
            config_manager=config_manager,
            calculation_service=calculation_service,
            fan_controller=fan_controller
        )
        
        return climate_chamber, sensor_reader
        
    except Exception as e:
        print(f"Error setting up peltier control: {e}")
        return None, None

def control_peltier(climate_chamber, duty_cycle_percent):
    """Control peltier at specific duty cycle."""
    if climate_chamber is None:
        print("Peltier control not available")
        return False
    
    try:
        # Enable peltier modules
        climate_chamber.enable_peltier_modules()
        print(f"Peltier modules enabled")
        
        # Apply control with specific duty cycle
        if duty_cycle_percent == 0:
            # Stop peltier (but keep enabled)
            control_data = {"pid_output": 0}
            climate_chamber.apply_control(control_data)
            print(f"Peltier set to 0% duty cycle (stopped)")
        else:
            # Apply heating with specified duty cycle
            control_data = {"pid_output": duty_cycle_percent}
            climate_chamber.apply_control(control_data)
            print(f"Peltier set to {duty_cycle_percent}% duty cycle (heating)")
        
        return True
        
    except Exception as e:
        print(f"Error controlling peltier: {e}")
        return False

def stop_peltier(climate_chamber):
    """Stop and disable peltier."""
    if climate_chamber is None:
        return
    
    try:
        climate_chamber.stop()
        print("Peltier stopped and disabled")
    except Exception as e:
        print(f"Error stopping peltier: {e}")

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

def calibrate_single_sensor(sensor_config, climate_chamber):
    """Calibrate a single current sensor at different duty cycles."""
    print(f"\n=== Calibrating {sensor_config.name} ===")
    
    # Create sensor instance
    sensor = ADS1115(sensor_config)
    
    calibration_results = []
    duty_cycles = [0, 5]  # Test at 0% and 5% duty cycle
    
    for duty_cycle in duty_cycles:
        print(f"\n--- Testing at {duty_cycle}% duty cycle ---")
        
        # Set peltier duty cycle
        if control_peltier(climate_chamber, duty_cycle):
            print(f"Waiting 3 seconds for current to stabilize...")
            time.sleep(3)
            
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
                        print(f"Measure actual current with multimeter at {duty_cycle}% duty cycle")
                        actual_current = float(input(f"Enter actual current (in A): "))
                        
                        # Store calibration data point
                        calibration_results.append({
                            'duty_cycle': duty_cycle,
                            'ads_reading': ads_reading,
                            'actual_current': actual_current
                        })
                        
                        # Run calibration for this data point
                        if hasattr(sensor, 'calibrate_current_sensor'):
                            calculated_sensitivity = sensor.calibrate_current_sensor(actual_current)
                            print(f"Calculated sensitivity for this point: {calculated_sensitivity:.3f} V/A")
                        
                    except ValueError:
                        print("Invalid input, skipping this measurement")
                else:
                    print(f"Could not read from sensor {sensor_config.name}")
            else:
                print(f"Sensor {sensor_config.name} not found in readings")
        else:
            print(f"Could not set peltier to {duty_cycle}% duty cycle")
    
    # Analyze calibration results
    if len(calibration_results) >= 2:
        print(f"\n=== CALIBRATION ANALYSIS for {sensor_config.name} ===")
        
        # Calculate average sensitivity from multiple points
        sensitivities = []
        for result in calibration_results:
            if result['actual_current'] != 0:  # Avoid division by zero
                # Calculate voltage above offset
                voltage_above_offset = result['ads_reading'] * sensor._sensitivity + sensor._voltage_offset - sensor._voltage_offset
                sensitivity = voltage_above_offset / result['actual_current']
                sensitivities.append(sensitivity)
                print(f"  {result['duty_cycle']}% duty: ADS={result['ads_reading']:.3f}A, Actual={result['actual_current']:.3f}A, Sensitivity={sensitivity:.3f}V/A")
        
        if sensitivities:
            avg_sensitivity = sum(sensitivities) / len(sensitivities)
            print(f"\nAverage calculated sensitivity: {avg_sensitivity:.3f} V/A")
            print(f"Current sensitivity in code: {sensor._sensitivity:.3f} V/A")
            print(f"\nRECOMMENDED UPDATE:")
            print(f"Change self._sensitivity from {sensor._sensitivity:.3f} to {avg_sensitivity:.3f}")
            return avg_sensitivity
    
    return None

def main():
    """Main calibration routine."""
    print("=== ADS1115 Current Sensor Calibration ===")
    print("This script will:")
    print("1. Enable peltier modules")
    print("2. Test at 0% and 5% duty cycles")
    print("3. Guide you through calibration measurements")
    print()
    print("Have a multimeter ready to measure actual current!")
    print()
    
    # Setup peltier control
    print("Setting up peltier control...")
    climate_chamber, sensor_reader = setup_peltier_control()
    
    if climate_chamber is None:
        print("ERROR: Could not setup peltier control. Exiting.")
        return
    
    try:
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
                result = calibrate_single_sensor(sensor_config, climate_chamber)
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
            
    finally:
        # Always stop peltier when done
        print("\nStopping peltier...")
        stop_peltier(climate_chamber)

if __name__ == "__main__":
    main()