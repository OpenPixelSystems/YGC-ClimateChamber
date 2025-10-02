# Climate Chamber Control System - Technical Documentation

A Flask-based climate chamber control system for Raspberry Pi providing precise temperature control using Peltier elements, real-time monitoring, and flow-based control sequences.

## Overview

This technical documentation is intended for developers and system administrators who need to understand the architecture, modify the system, or add new hardware components.

**For Users**: See `USER_GUIDE.md` for connection instructions and `INTERFACE_MANUAL.md` for application usage.

**Key Technologies:**
- Flask 3.1.1 web framework with Jinja2 templates
- RPi.GPIO for hardware control
- Adafruit CircuitPython libraries for sensors
- SQLite for data logging
- Chart.js for real-time visualization
- PID-based temperature control

---

## Architecture

### Frontend

The frontend is a Flask-rendered web application using HTML templates, JavaScript, and CSS.

**Location:** `app/frontend/`

**Technologies:**
- **Flask Templates (Jinja2)**: Server-side HTML rendering
- **JavaScript**: Client-side interactivity and real-time updates
- **CSS**: Custom styling with responsive design
- **AJAX**: Asynchronous communication with backend APIs

**Key Pages:**
- `home.html` - Main dashboard with quick temperature input
- `setupGraph.html` - Temperature profile creation interface
- `displayGraph.html` - Real-time graph display during active cycles
- `manualControl.html` - Manual hardware control interface
- `flow_designer.html` - Visual flow-based control designer
- `configEditor.html` - System configuration editor
- `databaseViewer.html` - Historical data viewer
- `logs_viewer.html` - System logs browser
- `wifi_networks.html` - WiFi network configuration

**Frontend Features:**
- Real-time temperature plotting using Chart.js or similar
- Drag-and-drop flow designer for creating temperature sequences
- Responsive forms for configuration editing
- Live status updates via periodic AJAX polling
- Flash messages for user feedback

---

### Backend

The backend follows a modular, interface-driven architecture with clear separation of concerns.

**Location:** `app/backend/`

**Technologies:**
- **Flask 3.1.1**: Web framework and API routing
- **RPi.GPIO**: Raspberry Pi GPIO control for hardware interfacing
- **Adafruit CircuitPython Libraries**:
  - `adafruit-circuitpython-mpl3115a2` - Pressure/temperature sensor
  - `adafruit-circuitpython-ads1x15` - Analog-to-Digital converter
- **SQLite**: Local database for data logging (`database.db`)
- **Python 3.x**: Core programming language

**Architecture Layers:**

#### 1. **Interfaces** (`app/backend/Interfaces/`)
Define contracts for all major components:
- `ISensor.py` - Sensor reading interface
- `IDriver.py` - Hardware driver interface
- `IClimateChamber.py` - Climate control interface
- `IConfigManager.py` - Configuration management
- `IDatabaseManager.py` - Database operations
- And more...

#### 2. **Implementations** (`app/backend/Implementations/`)
Concrete implementations of interfaces:
- `ClimateChamber.py` - Main climate control logic with PID control
- `ClimateChamberController.py` - High-level controller orchestration
- `SensorReader.py` - Reads all configured sensors
- `ConfigManager.py` - Loads and validates JSON configurations
- `DatabaseManager.py` - SQLite operations for logging and retrieval
- `FanController.py` - Fan speed control
- `RelayController.py` - Relay switching (e.g., for fridge control)

#### 3. **Drivers** (`app/backend/Drivers/`)
Low-level hardware drivers for motor controllers:
- `BTS7960Driver.py` - High-power motor driver for Peltier modules (up to 43A)
- `TB6612FNGDriver.py` - Dual motor driver for smaller Peltier/fan modules

#### 4. **Sensors** (`app/backend/Sensors/`)
Sensor implementations:
- `NTCTemperatureSensor.py` - NTC thermistor reading via ADC
- `DS18B20.py` - Digital temperature sensor (1-Wire)
- `DS18B20Cluster.py` - Multiple DS18B20 sensors
- `MPL3115A2.py` - I2C pressure and temperature sensor
- `ADS1115.py` - 16-bit ADC for analog sensors

#### 5. **Modules** (`app/backend/Modules/`)
Higher-level hardware abstractions:
- `PeltierModule.py` - Peltier element control (heating/cooling)
- `FanModule.py` - Fan control with PWM speed adjustment

#### 6. **Services** (`app/backend/Services/`)
Business logic and orchestration:
- `GuardingService.py` - Safety monitoring and emergency stops
- `TemperatuurService.py` - Temperature validation and processing
- `CalculationService.py` - PID calculations and control algorithms

#### 7. **Configuration** (`app/backend/config/`)
JSON-based configuration files:
- `raspberry_pi_config.json` - Hardware pin mappings and sensor definitions
- `control_config.json` - PID parameters and control settings
- `graph_config.json` - Stored temperature profiles

#### 8. **Flow Execution** (`app/backend/FlowExecution/`)
- `FlowExecutor.py` - Executes visual flow-based temperature sequences

#### 9. **Application State** (`app/backend/app_state.py`)
Singleton pattern for managing global application state:
- Initializes all components via factory methods
- Provides shared access to services and controllers
- Handles system reload and restart operations

---

## How It Works

### 1. **Temperature Control Loop**

The system uses a PID (Proportional-Integral-Derivative) control loop:

1. **Sensor Reading**: `SensorReader` polls all configured temperature sensors
2. **Calculation**: `CalculationService` compares current vs. desired temperature and calculates PID output
3. **Hardware Control**: Based on PID output:
   - **Positive output** → Heat mode: Peltier modules heat, fridge relay OFF
   - **Negative output** → Cool mode: Peltier modules cool or fridge relay ON
4. **Safety Monitoring**: `GuardingService` continuously checks sensor limits
5. **Logging**: `DatabaseManager` records all data points to SQLite database

### 2. **Peltier Module Control**

Peltier elements are thermoelectric devices that can heat or cool based on current direction:

- **Heating**: Current flows one direction (RPWM active, LPWM off)
- **Cooling**: Current flows opposite direction (LPWM active, RPWM off)
- **PWM Duty Cycle**: Controls heating/cooling intensity (0-100%)
- **Driver Selection**: System supports BTS7960 (high power) or TB6612FNG (lower power)

### 3. **Web Interface Communication**

1. User creates temperature profile via web interface
2. Frontend sends AJAX request to Flask route
3. Route handler validates input and calls backend service
4. Backend starts control loop and begins logging
5. Frontend polls for updates and renders real-time graphs

### 4. **Configuration System**

All hardware is defined in `raspberry_pi_config.json`:
```json
{
  "Temperature_inside_top": {
    "type": "NTC",
    "editable": {
      "SDA": 2,
      "SCL": 3,
      "read_pin": 0,
      "i2c_address": "0x4A",
      "beta_coefficient": 3600.0
    }
  },
  "Peltier_240W": {
    "type": "peltier",
    "editable": {
      "driver_type": "BTS7960",
      "RPWM": 13,
      "LPWM": 19,
      "R_EN": 5,
      "L_EN": 6,
      "PWM_FREQUENCY": 5000,
      "Duty cycle limit": 100
    }
  }
}
```

---

## Hardware Configuration

### Supported Hardware Components

#### **Temperature Sensors**
- **NTC Thermistors**: Via ADS1115 16-bit ADC
- **DS18B20**: Digital 1-Wire temperature sensors
- **MPL3115A2**: I2C pressure and temperature sensor

#### **Peltier Drivers**
- **BTS7960**: High-current (up to 43A) dual H-bridge for large Peltier modules
- **TB6612FNG**: Dual DC motor driver for smaller modules

#### **Other Components**
- **Fans**: PWM-controlled cooling fans
- **Relays**: For controlling external devices (e.g., refrigerator)

---

## Adapting to Different Hardware

### Adding a New Sensor

1. **Create sensor class** in `app/backend/Sensors/`:
```python
from app.backend.Interfaces.ISensor import ISensor

class MySensor(ISensor):
    def __init__(self, config):
        self.config = config

    def read(self):
        # Your sensor reading logic
        return temperature_value
```

2. **Add to SensorReader** in `app/backend/Implementations/SensorReader.py`:
```python
elif sensor_config.type == "MySensor":
    from app.backend.Sensors.MySensor import MySensor
    sensor = MySensor(sensor_config)
```

3. **Update configuration** in `raspberry_pi_config.json`:
```json
{
  "My_Temperature_Sensor": {
    "name": "My_Temperature_Sensor",
    "type": "MySensor",
    "editable": {
      "gpio_pin": 17,
      "custom_parameter": 123
    },
    "unit": "degrees"
  }
}
```

### Adding a New Motor Driver

1. **Create driver class** in `app/backend/Drivers/`:
```python
from app.backend.Interfaces.IDriver import IDriver

class MyDriver(IDriver):
    def __init__(self, config):
        # Initialize GPIO pins
        pass

    def heat(self, duty_cycle):
        # Implement heating logic
        pass

    def cool(self, duty_cycle):
        # Implement cooling logic
        pass

    def stop(self):
        # Stop all outputs
        pass
```

2. **Add to PeltierModule** in `app/backend/Modules/PeltierModule.py`:
```python
class DriverType(Enum):
    TB6612FNG = "TB6612FNG"
    BTS7960 = "BTS7960"
    MY_DRIVER = "MY_DRIVER"  # Add your driver

# In __init__:
if self.driver_type == DriverType.MY_DRIVER.value:
    from app.backend.Drivers.MyDriver import MyDriver
    self.driver = MyDriver(config)
```

3. **Update configuration**:
```json
{
  "Peltier_Custom": {
    "type": "peltier",
    "editable": {
      "driver_type": "MY_DRIVER",
      "pin1": 13,
      "pin2": 19,
      "pwm_frequency": 5000
    }
  }
}
```

### Changing GPIO Pin Assignments

Edit `app/backend/config/raspberry_pi_config.json` to change pin numbers:
```json
{
  "Peltier_240W": {
    "editable": {
      "RPWM": 13,  // Change to your pin number
      "LPWM": 19,  // Change to your pin number
      "R_EN": 5,
      "L_EN": 6
    }
  }
}
```

**Important**: After changing GPIO pins, restart the service:
```bash
sudo systemctl restart climatechamber.service
```

---

## Development Setup

### Local Development

1. Clone repository and create virtual environment:
```bash
git clone https://gitlab.com/tmc-climatechamber/climatechamber.git
cd climatechamber
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

2. Run development server:
```bash
python run.py
```

3. Access at `http://localhost:5000`

### Raspberry Pi Deployment

The system is pre-configured to run as a systemd service on Raspberry Pi. For fresh installations:

1. Clone repository on Raspberry Pi
2. Run setup script: `./setup_rp4.sh`
3. Service starts automatically on boot

---

## Project Structure

```
climatechamber/
├── app/
│   ├── __init__.py                 # Flask app factory
│   ├── backend/
│   │   ├── app_state.py            # Singleton application state
│   │   ├── Dataclasses/            # Data models and configurations
│   │   ├── Drivers/                # Low-level hardware drivers
│   │   ├── Sensors/                # Sensor implementations
│   │   ├── Modules/                # Hardware module abstractions
│   │   ├── Implementations/        # Core business logic
│   │   ├── Interfaces/             # Abstract interfaces
│   │   ├── Services/               # Business services
│   │   ├── FlowExecution/          # Flow-based control
│   │   ├── Providers/              # GPIO and hardware providers
│   │   ├── Technical/              # Logging and utilities
│   │   └── config/                 # JSON configuration files
│   ├── frontend/
│   │   ├── static/                 # CSS, JS, fonts
│   │   └── templates/              # HTML templates
│   └── routes/                     # Flask route handlers
├── run.py                          # Application entry point
├── requirements.txt                # Python dependencies
├── database.db                     # SQLite database
├── setup_rp4.sh                    # Raspberry Pi setup script
└── README.md                       # This file
```

---

## API Routes

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Home page with quick temperature input |
| `/status` | GET | Health check endpoint |
| `/submit-temperature` | POST | Start constant temperature cycle |
| `/manual-control` | GET | Manual hardware control interface |
| `/setup-graph` | GET/POST | Create temperature profiles |
| `/display-graph` | GET | Real-time monitoring |
| `/flow-designer` | GET/POST | Visual flow designer |
| `/database-viewer` | GET | View historical data |
| `/config-editor` | GET/POST | Edit system configuration |
| `/logs` | GET | View system logs |
| `/wifi` | GET/POST | Manage WiFi connections |

---

## Configuration Files

### raspberry_pi_config.json
Defines all hardware components and GPIO pin mappings.

### control_config.json
Contains PID tuning parameters and control loop settings.

### graph_config.json
Stores saved temperature profiles.

---

## Safety Features

1. **Temperature Limits**: Configurable min/max values per sensor
2. **Safety-Critical Sensors**: Emergency stops if limits exceeded
3. **Guarding Service**: Continuous monitoring of all sensors
4. **Emergency Stop**: Immediate hardware shutdown capability
5. **Duty Cycle Limits**: Prevents over-driving Peltier elements
6. **Cycle Locking**: Prevents starting multiple cycles simultaneously

---

## Development

### Adding New Features

The system follows the **Interface-Implementation pattern**:
1. Define interface in `Interfaces/`
2. Create implementation in `Implementations/`
3. Register in `app_state.py` factory methods
4. Add route handler in `routes/`
5. Create frontend template if needed

### Testing

Unit tests are located in `unittest/` directory.

---

## Common Development Issues

### GPIO Permission Errors
```bash
sudo usermod -a -G gpio $USER
# Log out and back in for changes to take effect
```

### I2C Not Enabled
```bash
sudo raspi-config
# Interface Options → I2C → Enable
```

### Service Debugging
```bash
# View real-time logs
sudo journalctl -u climatechamber.service -f

# Check service status
sudo systemctl status climatechamber.service

# Restart service
sudo systemctl restart climatechamber.service
```

### Python Import Errors
Ensure virtual environment is activated and all dependencies are installed:
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Contributing

When adding new features:
1. Follow the Interface-Implementation pattern
2. Add corresponding route handlers in `app/routes/`
3. Update frontend templates as needed
4. Document changes in code comments
5. Test thoroughly before committing

---

## License

[Add your license information here]

## Support

For technical issues, check the logs and review this documentation. For user-facing questions, direct users to `USER_GUIDE.md` and `INTERFACE_MANUAL.md`.
