#!/usr/bin/env python3
"""
ADS1115 ADC Reader for Raspberry Pi
Reads analog values from specified channel using I2C communication
"""

import time
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn


def get_user_input():
    """Get configuration from user input"""
    print("ADS1115 ADC Reader Configuration")
    print("=" * 40)

    # Get I2C address
    print("\nAvailable I2C addresses:")
    print("1. 0x48 (ADDR connected to GND - default)")
    print("2. 0x49 (ADDR connected to VDD)")
    print("3. 0x4A (ADDR connected to SDA)")
    print("4. 0x4B (ADDR connected to SCL)")

    while True:
        try:
            addr_choice = input("Select I2C address (1-4) [default: 1]: ").strip()
            if addr_choice == "":
                addr_choice = "1"

            addr_map = {"1": 0x48, "2": 0x49, "3": 0x4A, "4": 0x4B}
            if addr_choice in addr_map:
                i2c_address = addr_map[addr_choice]
                break
            else:
                print("Please enter 1, 2, 3, or 4")
        except KeyboardInterrupt:
            print("\nProgram interrupted by user")
            exit()

    # Get channel
    print("\nAvailable channels:")
    print("0. A0")
    print("1. A1")
    print("2. A2")
    print("3. A3")

    while True:
        try:
            channel = input("Select channel (0-3) [default: 0]: ").strip()
            if channel == "":
                channel = 0
            else:
                channel = int(channel)

            if channel in [0, 1, 2, 3]:
                break
            else:
                print("Please enter 0, 1, 2, or 3")
        except ValueError:
            print("Please enter a valid number (0-3)")
        except KeyboardInterrupt:
            print("\nProgram interrupted by user")
            exit()

    # Get gain
    print("\nAvailable gain settings:")
    print("1. 2/3 (±6.144V)")
    print("2. 1   (±4.096V) - default")
    print("3. 2   (±2.048V)")
    print("4. 4   (±1.024V)")
    print("5. 8   (±0.512V)")
    print("6. 16  (±0.256V)")

    while True:
        try:
            gain_choice = input("Select gain (1-6) [default: 2]: ").strip()
            if gain_choice == "":
                gain_choice = "2"

            gain_map = {"1": 2 / 3, "2": 1, "3": 2, "4": 4, "5": 8, "6": 16}
            if gain_choice in gain_map:
                gain = gain_map[gain_choice]
                break
            else:
                print("Please enter 1, 2, 3, 4, 5, or 6")
        except KeyboardInterrupt:
            print("\nProgram interrupted by user")
            exit()

    # Get reading interval
    while True:
        try:
            interval_input = input("Reading interval in seconds [default: 0.5]: ").strip()
            if interval_input == "":
                interval = 0.5
            else:
                interval = float(interval_input)
                if interval <= 0:
                    print("Interval must be greater than 0")
                    continue
            break
        except ValueError:
            print("Please enter a valid number")
        except KeyboardInterrupt:
            print("\nProgram interrupted by user")
            exit()

    return i2c_address, channel, gain, interval


def get_channel_pin(channel):
    """Convert channel number to ADS pin"""
    pins = {0: ADS.P0, 1: ADS.P1, 2: ADS.P2, 3: ADS.P3}
    return pins[channel]


def get_voltage_range(gain):
    """Get voltage range for given gain"""
    ranges = {2 / 3: 6.144, 1: 4.096, 2: 2.048, 4: 1.024, 8: 0.512, 16: 0.256}
    return ranges[gain]


def main():
    # Get configuration from user
    i2c_address, channel, gain, interval = get_user_input()

    try:

        # Configure gain (optional)
        # ads.gain = 1  # +/-4.096V range (default)
        # Other options: 2/3 (+/-6.144V), 1 (+/-4.096V), 2 (+/-2.048V),
        #                4 (+/-1.024V), 8 (+/-0.512V), 16 (+/-0.256V)
        # Create the I2C bus
        i2c = busio.I2C(board.SCL, board.SDA)

        # Create the ADS object
        ads = ADS.ADS1115(i2c, address=i2c_address)

        # Set gain
        ads.gain = gain

        # Create single-ended input on specified channel
        channel_pin = get_channel_pin(channel)
        adc_channel = AnalogIn(ads, channel_pin)

        # Display configuration
        voltage_range = get_voltage_range(gain)
        print("\n" + "=" * 50)
        print("ADS1115 ADC Reader - Starting Measurements")
        print("=" * 50)
        print(f"I2C Address: 0x{i2c_address:02X}")
        print(f"Channel: A{channel}")
        print(f"Gain: {gain} (±{voltage_range}V range)")
        print(f"Read Interval: {interval}s")
        print("=" * 50)
        print("Press Ctrl+C to exit")
        print("-" * 50)

        while True:
            # Read the raw ADC value and voltage
            raw_value = adc_channel.value
            voltage = adc_channel.voltage

            # Print the readings
            print(f"Channel A{channel} | Raw: {raw_value:5d} | Voltage: {voltage:.4f}V")

            # Wait before next reading
            time.sleep(interval)

    except ValueError as e:
        print(f"Error with configuration: {e}")

    except KeyboardInterrupt:
        print("\nProgram interrupted by user")

    except Exception as e:
        print(f"Error: {e}")
        print("Make sure:")
        print("- I2C is enabled on your Raspberry Pi")
        print("- ADS1115 is properly connected")
        print("- Correct I2C address is used")
        print("- Use 'i2cdetect -y 1' to scan for I2C devices")


if __name__ == "__main__":
    main()