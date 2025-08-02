#!/usr/bin/env python3
"""
ADS1115 Current Sensor Test Script
Tests current readings when motor is fully off to debug 4A issue
"""

import time
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import RPi.GPIO as GPIO

# Configuration from your JSON
# BTS7960 Driver pins
RPWM_PIN = 13  # Right PWM (forward direction)
LPWM_PIN = 19  # Left PWM (reverse direction)
R_EN_PIN = 5  # Right enable
L_EN_PIN = 6  # Left enable
PWM_FREQUENCY = 5000  # 5kHz

# ADS1115 Current sensors (all on same I2C bus)
CURRENT_SENSORS = {
    0: "R_IS_1_Current_sensor",  # A0 - Right current sensor 1
    1: "L_IS_1_Current_sensor",  # A1 - Left current sensor 1
    2: "R_IS_2_Current_sensor",  # A2 - Right current sensor 2
    3: "L_IS_2_Current_sensor"  # A3 - Left current sensor 2
}

# Current conversion factors (from your ADS1115 implementation)
VOLTAGE_OFFSET = 1.65  # Offset voltage (V) - typically Vcc/2
SENSITIVITY = 0.1  # Sensitivity (V/A) - depends on current sensor model


def setup_hardware():
    """Initialize ADS1115 and GPIO"""
    print("Setting up hardware...")

    # Setup I2C and ADS1115 (matching your implementation)
    i2c = busio.I2C(board.SCL, board.SDA)
    ads = ADS.ADS1115(i2c, address=0x48)  # Default I2C address from your code

    # Configure ADS gain and data rate (matching your implementation)
    ads.gain = 1  # ±4.096V range
    ads.data_rate = 128  # 128 SPS

    # Setup all 4 ADS channels
    channels = {}
    for i in range(4):
        channels[i] = AnalogIn(ads, getattr(ADS, f'P{i}'))

    # Setup GPIO for BTS7960
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(RPWM_PIN, GPIO.OUT)  # Right PWM
    GPIO.setup(LPWM_PIN, GPIO.OUT)  # Left PWM
    GPIO.setup(R_EN_PIN, GPIO.OUT)  # Right enable
    GPIO.setup(L_EN_PIN, GPIO.OUT)  # Left enable

    # Create PWM instances for both directions
    rpwm = GPIO.PWM(RPWM_PIN, PWM_FREQUENCY)  # Right PWM
    lpwm = GPIO.PWM(LPWM_PIN, PWM_FREQUENCY)  # Left PWM

    return ads, channels, rpwm, lpwm


def voltage_to_current(voltage: float) -> float:
    """Convert voltage reading to current using your implementation's formula"""
    # Current = (Voltage - Offset) / Sensitivity (from your ADS1115 class)
    current = (voltage - VOLTAGE_OFFSET) / SENSITIVITY
    return current


def ensure_motor_off(rpwm, lpwm):
    """Ensure motor driver is idle but enabled"""
    print("Setting motor driver to IDLE state...")

    # Enable both directions (driver ready but idle)
    GPIO.output(R_EN_PIN, GPIO.HIGH)
    GPIO.output(L_EN_PIN, GPIO.HIGH)

    # Set PWM to 0% (no movement)
    rpwm.start(0)
    lpwm.start(0)

    print("✓ PWM set to 0% (idle)")
    print("✓ Enable pins set HIGH (driver enabled but idle)")
    print("✓ Motor should be stationary with zero current draw")


def read_all_channels(channels, samples=10):
    """Read all ADS channels with multiple samples"""
    print(f"Reading all 4 ADS channels ({samples} samples each)...")

    channel_data = {}

    for channel_num in range(4):
        voltages = []
        currents = []

        print(f"  Reading A{channel_num}...", end=" ")

        for i in range(samples):
            # Read raw voltage from ADS
            voltage = channels[channel_num].voltage
            voltages.append(voltage)

            # Convert to current using your implementation's formula
            current = voltage_to_current(voltage)
            currents.append(current)

            time.sleep(0.05)  # Small delay between readings

        avg_voltage = sum(voltages) / len(voltages)
        avg_current = sum(currents) / len(currents)

        channel_data[channel_num] = {
            'voltages': voltages,
            'currents': currents,
            'avg_voltage': avg_voltage,
            'avg_current': avg_current
        }

        print(f"Done (Avg: {avg_voltage:.4f}V, {avg_current:.4f}A)")

    return channel_data


def main():
    """Main test function"""
    print("=" * 60)
    print("ADS1115 ALL CHANNELS Current Sensor Debug Test")
    print("=" * 60)
    print(f"Voltage offset: {VOLTAGE_OFFSET} V")
    print(f"Sensitivity: {SENSITIVITY} V/A")
    print("Using your ADS1115 implementation's conversion formula")
    print("Testing BTS7960 in IDLE state (enabled but 0% PWM)")
    print()

    try:
        # Setup hardware
        ads, channels, rpwm, lpwm = setup_hardware()

        # Set motor driver to idle state
        ensure_motor_off(rpwm, lpwm)

        print("\nWaiting 2 seconds for system to stabilize...")
        time.sleep(2)

        # Test 1: Read all channels with motor idle
        print("\n" + "=" * 40)
        print("TEST 1: All Channels - Motor IDLE")
        print("=" * 40)

        channel_data = read_all_channels(channels, 10)

        # Display results for each channel
        print("\nDetailed Results:")
        print("-" * 50)

        problematic_channels = []

        for channel_num in range(4):
            data = channel_data[channel_num]
            sensor_name = CURRENT_SENSORS[channel_num]
            print(f"\nChannel A{channel_num} ({sensor_name}):")
            print(f"  Raw voltages: {[f'{v:.4f}' for v in data['voltages'][:5]]}... (showing first 5)")
            print(f"  Calculated currents: {[f'{c:.4f}' for c in data['currents'][:5]]}... (showing first 5)")
            print(f"  Average voltage: {data['avg_voltage']:.4f} V")
            print(f"  Average current: {data['avg_current']:.4f} A")

            # Check if current is abnormally high
            if abs(data['avg_current']) > 0.1:  # More than 100mA when idle
                print(f"  ⚠️  WARNING: High current on A{channel_num} ({sensor_name})!")
                problematic_channels.append(channel_num)
            else:
                print(f"  ✓ Normal reading for idle state")

        # Summary
        print("\n" + "=" * 40)
        print("SUMMARY")
        print("=" * 40)

        if problematic_channels:
            problem_sensors = [CURRENT_SENSORS[ch] for ch in problematic_channels]
            print(f"⚠️  Channels with abnormal readings:")
            for ch in problematic_channels:
                print(f"     A{ch}: {CURRENT_SENSORS[ch]}")

            print("\nPossible issues:")
            print("- Voltage offset is incorrect (currently 1.65V)")
            print("- Sensitivity is wrong (currently 0.1 V/A)")
            print("- BTS7960 IS pins don't output 1.65V at 0A")
            print("- Current sensor calibration mismatch")
            print("- Hardware issue with BTS7960 current sensing")
            print("- Wrong wiring between BTS7960 IS pins and ADS channels")
            print(f"\nNote: Your formula expects 0A at {VOLTAGE_OFFSET}V")
            print(f"Any voltage != {VOLTAGE_OFFSET}V will show current!")
            print("\nBTS7960 IS pins typically output:")
            print("- 0V to 3.3V proportional to current")
            print("- NOT centered at 1.65V for 0A")
        else:
            print("✓ All channels show normal readings for idle motor state")

        # Test 2: Check ADS configuration
        print("\n" + "=" * 40)
        print("TEST 2: ADS1115 Configuration")
        print("=" * 40)
        print(f"ADS Gain: {ads.gain}")
        print(f"Voltage range: ±{4.096 / ads.gain:.3f} V")
        print(f"Resolution: {(4.096 / ads.gain) / 32768:.6f} V/bit")

        # Test 3: Raw ADS readings for all channels
        print("\n" + "=" * 40)
        print("TEST 3: Raw ADS Values (All Channels)")
        print("=" * 40)
        for channel_num in range(4):
            channel = channels[channel_num]
            print(f"Channel A{channel_num}:")
            print(f"  Raw ADC value: {channel.value}")
            print(f"  Reference voltage: {channel.reference_voltage:.4f} V")
            print(f"  Current voltage: {channel.voltage:.4f} V")

        # Test 4: Recommendations
        print("\n" + "=" * 40)
        print("TEST 4: Next Steps")
        print("=" * 40)
        print("Recommended actions:")
        print("1. Check BTS7960 datasheet for R_IS/L_IS pin specifications")
        print("2. Measure IS pin voltages directly with multimeter when idle")
        print("3. BTS7960 IS pins likely output 0-3.3V, NOT centered at 1.65V")
        print("4. Consider using 0V offset instead of 1.65V")
        print("5. Verify sensitivity value matches your current sensor specs")
        print("6. Test with known current load to calibrate properly")

        if problematic_channels:
            sensor_names = [CURRENT_SENSORS[ch] for ch in problematic_channels]
            print(f"\nFocus debugging on these sensors: {', '.join(sensor_names)}")
            print(f"Corresponding ADS channels: A{', A'.join(map(str, problematic_channels))}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Cleanup
        try:
            rpwm.stop()
            lpwm.stop()
            GPIO.cleanup()
            print("\nTest complete. GPIO cleaned up.")
        except:
            pass


if __name__ == "__main__":
    main()