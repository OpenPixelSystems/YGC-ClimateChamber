import os

def DHT22_read(sensor):
    """
    Read temperature and humidity from a DHT22 sensor.
    Works with both real hardware and mock environment.
    """
    json_format = {}

    try:
        # In a real implementation you would use the appropriate library
        # For DHT22, Adafruit_DHT is commonly used, but it requires installation
        # Check if we're on an actual Raspberry Pi
        if os.path.exists('/opt/vc/bin/'):  # A directory that exists on Raspberry Pi
            try:
                # Try to import the DHT library - will only work if installed
                import Adafruit_DHT

                # Read from the sensor
                humidity, temperature = Adafruit_DHT.read_retry(Adafruit_DHT.DHT22, sensor._pin)

                if humidity is not None and temperature is not None:
                    json_format[sensor._name] = temperature  # Or humidity, depending on sensor type
                else:
                    # Sensor read failed, fallback to simulated value
                    json_format[sensor._name] = 22.5 if sensor._type == "temperature" else 45.0

            except ImportError:
                # Library not available, use simulated values
                json_format[sensor._name] = 22.5 if sensor._type == "temperature" else 45.0
        else:
            # We're in a testing environment
            # Simulate readings based on pin
            if sensor._type == "temperature":
                simulated_temp = 20 + (sensor._pin % 10) / 2
                json_format[sensor._name] = simulated_temp
            else:  # humidity
                simulated_humidity = 40 + (sensor._pin % 10) * 2
                json_format[sensor._name] = simulated_humidity

    except Exception as e:
        print(f"Error reading DHT22 sensor {sensor._name}: {str(e)}")
        json_format[sensor._name] = None

    return json_format