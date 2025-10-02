# Climate Chamber Interface Manual

Complete guide to using the Climate Chamber web interface.

---

## Getting Started

After connecting to the Raspberry Pi (see USER_GUIDE.md), open a web browser and navigate to:

**URL**: `http://192.168.137.1:5000`

The interface provides multiple ways to control temperature:
- **Quick Constant Temperature** - Maintain a single temperature
- **Manual Control** - Direct power control of Peltier elements
- **Graph Setup** - Create time-based temperature profiles
- **Temperature Flow** - Visual flow-based temperature sequences

---

## Table of Contents

1. [Navigation Bar](#navigation-bar)
2. [Home Page](#home-page)
3. [Manual Control](#manual-control)
4. [Graph Setup](#graph-setup)
5. [Temperature Flow Designer](#temperature-flow-designer)
6. [Active Cycle Monitoring](#active-cycle-monitoring)
7. [Database Viewer](#database-viewer)
8. [Configuration Editor](#configuration-editor)
9. [Logs Viewer](#logs-viewer)

---

## Navigation Bar

The navigation bar appears at the top of every page and provides quick access to all major features.

### Main Navigation Links

- **Home** - Return to the main dashboard
- **Graph Setup** - Create custom temperature profiles
- **Temperature Flow** - Visual flow-based temperature sequence designer
- **Database Viewer** - View and analyze historical cycle data
- **Logs** - System logs and diagnostics
- **Active Cycle** (dynamic) - Appears only when a cycle is running; click to return to the active monitoring page

### Control Icons (Right Side)

1. **Storage Indicator** 💾
   - Shows current storage usage percentage
   - Visual bar indicates disk space used
   - Hover for detailed storage information

2. **WiFi Button** 🛈
   - Access WiFi network configuration
   - **Note**: WiFi configuration doesn't work when running as a service - use Ethernet connection instead

3. **Settings Gear** ⚙️
   - Opens System Configuration Editor
   - Edit JSON configuration files
   - Restart the Climate Chamber service

4. **Restart Button** 🔄
   - Restart the Climate Chamber service
   - Use when configuration changes require a full restart
   - System will be unavailable for 30-60 seconds

5. **Dark Mode Toggle** 🌓
   - Switch between light and dark themes
   - Preference is saved in browser

---

## Home Page

The home page provides quick access to start a constant temperature cycle or begin manual control.

### IP Address Display
- Shows the Raspberry Pi's current IP address at the top
- Use this address to connect from other devices on the network

### Quick Temperature Set

**Purpose**: Start a cycle that maintains a constant temperature.

**How to Use**:
1. Enter desired temperature in °C (decimal values supported, e.g., 25.5)
2. Click "Set Constant Temperature"
3. System validates the temperature is within safe limits
4. If valid, redirects to Active Cycle Monitoring page
5. Chamber will heat or cool to reach and maintain the target temperature

**Limitations**:
- Only one cycle can run at a time
- If a cycle is active, this button is disabled
- Temperature must be within configured min/max range

### Manual Control Button

**Purpose**: Access direct hardware control without predefined temperature profiles.

**How to Use**:
1. Click "Start manual control"
2. Opens Manual Control interface (see section below)
3. Provides direct power control over Peltier elements

**When Disabled**:
- Button is disabled if another cycle is running from a different page
- Stop the current cycle first, then access manual control

---

## Manual Control

Manual Control provides direct power management over the Peltier elements without automated temperature targeting.

### Enable Peltier Elements

**Critical First Step**:
- ✅ **Check the "Enable Peltier Elements" checkbox** before any control will work
- This is a safety feature to prevent accidental activation
- Peltier elements will NOT respond to power commands unless enabled

### Power Control Slider

**Range**: -100 to +100
- **Positive values (0 to +100)**: Heating mode
  - Higher values = more heating power
  - Example: +50 = 50% heating duty cycle
- **Negative values (-100 to 0)**: Cooling mode
  - Lower values = more cooling power
  - Example: -75 = 75% cooling duty cycle
- **Zero (0)**: Peltier elements stopped

**How to Use**:
1. Enable Peltier elements checkbox
2. Drag slider to desired power level
3. Value updates visually as you drag
4. Release slider to send command to hardware
5. Monitor temperature changes in real-time graph

### Start/Stop Cycle

**Start Cycle Button**:
- Begins sensor data logging
- Starts real-time graph updates
- Changes to "Stop Cycle" button

**Stop Cycle Button**:
- Stops data logging
- Clears the current graph
- Resets to "Start Cycle" button

### Real-Time Graph

- Displays all sensor readings in real-time
- X-axis: Time elapsed since cycle start
- Y-axis: Temperature (°C) or sensor values
- Multiple lines for different sensors (color-coded)
- Updates continuously while cycle is running

**Graph Features**:
- Auto-scaling based on data range
- Legend shows which line represents which sensor
- Hover over data points for exact values

---

## Graph Setup

Graph Setup allows you to create custom temperature profiles with multiple temperature points over time.

### Starting Temperature

**Display**:
- Shows current average inside chamber temperature
- Updates automatically when page loads
- Click "Refresh" button to get latest reading

**Purpose**: Helps you plan realistic temperature transitions from current conditions

### Add Temperature Points

Create your temperature profile by adding sequential points:

**Temperature Input**:
- Enter target temperature in °C
- Supports decimal values (e.g., 35.5)

**Time Offset Input**:
- Specify time from previous point
- Supported formats:
  - `30s` - 30 seconds
  - `5m` - 5 minutes
  - `2h` - 2 hours
  - `90m` - 90 minutes (converted to 1.5 hours)

**Add Point Button**:
- Adds point to the graph
- Graph updates immediately
- Point is connected to previous point with a line

**Undo Last Button**:
- Removes the most recently added point
- Can be clicked multiple times to remove multiple points

### Interpolation Method

Choose how the system transitions between temperature points:

**Linear** (default):
- Straight line between points
- Constant rate of temperature change
- Predictable and simple

**Smooth (Monotone)**:
- Curved transitions between points
- More gradual temperature changes
- Prevents overshoot

### Graph Actions

**Clear All Points**:
- Removes all temperature points from graph
- Resets to empty state
- Starting point remains

**Save Graph to Server**:
- Validates the temperature profile
- Checks rate of change (rico) limits
- Stores profile for execution
- Redirects to Active Cycle Monitoring page

### Visual Graph Editor

- **X-axis**: Time (hours:minutes)
- **Y-axis**: Temperature (°C)
- Shows all added points connected by lines
- First point always starts at current chamber temperature
- Hover over points to see exact time and temperature values

**Validation**:
- System checks if heating/cooling rates are achievable
- Warns if temperature changes too quickly
- Prevents profiles that exceed hardware capabilities

---

## Temperature Flow Designer

The Flow Designer provides a visual, node-based interface for creating complex temperature sequences.

### Node Palette (Left Panel)

Drag nodes from the palette onto the canvas to build your flow.

#### Control Nodes

**Start Node** ▶
- Required: Every flow must begin with a Start Node
- Automatically reads current chamber temperature
- Only one Start Node allowed per flow

**End Node** ■
- Required: Every flow must end with an End Node
- Marks completion of the temperature cycle
- Only one End Node allowed per flow

#### Temperature Nodes

**Temperature Goal** ◎
- Sets a target temperature to reach
- System calculates time to reach target based on heating/cooling rates
- Configurable parameters:
  - **Target Temperature**: Desired temperature in °C (-40 to 100)
  - **Tolerance**: Acceptable deviation (±0.1 to ±5°C)
  - **Estimated Duration**: Automatically calculated

**Temperature Hold** ⏸
- Maintains temperature for a specified duration
- Temperature is inherited from previous node
- Configurable parameters:
  - **Hold Temperature**: Inherited from previous node (displayed but not editable)
  - **Duration**: How long to hold in minutes (1-1440)
  - **Tolerance**: Acceptable deviation (±0.1 to ±5°C)

### Design Canvas (Center)

**Adding Nodes**:
1. Drag a node from the palette
2. Drop it onto the canvas
3. Node appears with default settings

**Connecting Nodes**:
1. Click on the output port (right side) of a node
2. Drag to the input port (left side) of the next node
3. Arrow line appears showing the connection
4. Flow must be sequential: Start → Temperature nodes → End

**Moving Nodes**:
- Click and drag nodes to reposition
- Connections automatically update

**Deleting Nodes**:
- Select a node
- Press Delete key or use delete option

### Properties Panel (Right Panel)

**Node Selection**:
- Click any node on the canvas to edit its properties
- Properties panel shows settings for selected node
- Changes are saved automatically

**Start Node Properties**:
- Displays current chamber temperature (read-only)
- Temperature is fetched when node is selected

**Temperature Goal Properties**:
- Target Temperature: Input field for desired temperature
- Tolerance: Acceptable deviation range
- Estimated Duration: Calculated based on current chamber temperature and heating/cooling rates

**Temperature Hold Properties**:
- Inherited Temperature: Shows temperature from previous node
- Duration: Minutes to hold the temperature
- Tolerance: Acceptable deviation range

**End Node Properties**:
- No configurable settings
- Information only

### Flow Actions (Top Buttons)

**Clear Canvas**:
- Removes all nodes from canvas
- Resets flow to empty state
- Confirmation dialog prevents accidental clearing

**Validate Flow**:
- Checks flow structure is valid:
  - Has Start Node
  - Has End Node
  - All nodes are connected
  - No circular loops
  - Temperature transitions are achievable
- Displays validation results

**Save Flow**:
- Saves current flow diagram to local storage
- Prompts for flow name
- Can be loaded later

**Load Flow**:
- Shows list of saved flows
- Select a flow to load onto canvas
- Replaces current canvas content

**Export to Server**:
- Validates flow structure
- Converts to executable format
- Sends to server for execution
- Redirects to Flow Execution page

### Flow Status (Bottom Bar)

- **Flow Status**: Empty / Valid / Invalid
- **Total Nodes**: Count of nodes on canvas
- **Estimated Duration**: Total time for complete flow (calculated from all nodes)

### Example Flow

Simple heating and hold sequence:
1. **Start Node** (reads current temp, e.g., 20°C)
2. → **Temperature Goal** (target: 50°C, tolerance: ±0.5°C)
3. → **Temperature Hold** (hold 50°C for 30 minutes)
4. → **Temperature Goal** (target: 25°C, tolerance: ±0.5°C)
5. → **End Node**

---

## Active Cycle Monitoring

When any cycle is started (constant temperature, graph-based, flow-based, or manual), you are taken to the Active Cycle Monitoring page.

### Cycle Information

**Cycle Name**:
- Auto-generated: "Temperature cycle DD/MM/YYYY-HH:MM:SS"
- Custom names can be provided when starting some cycle types
- Input field at top of page (optional)

**Enable Peltier Elements Checkbox**:
- Same as Manual Control
- Must be checked for Peltier elements to operate
- Safety feature

### Control Buttons

**Start Cycle**:
- Begins the temperature control cycle
- Starts data logging to database
- Enables PID control (for graph/flow modes)
- Button changes to "Stop Cycle"

**Stop Cycle**:
- Stops temperature control
- Stops data logging
- Peltier elements are stopped
- Cycle data is saved to database
- Button changes to "Start Cycle"

### Real-Time Graph

**Display Features**:
- Multiple sensor lines (temperature, current, calculations)
- Desired temperature path (if using graph/flow mode)
- Time on X-axis (elapsed time since start)
- Temperature/values on Y-axis
- Auto-scaling

**Graph Interactions**:
- Zoom: Drag to select time range
- Pan: Click and drag when zoomed
- Reset: Double-click graph or use Reset Zoom button
- Hover: See exact values at any point

**Sensor List**:
- Below the control panel
- Shows all active sensors
- Real-time values update
- Color-coded to match graph lines

### Active Cycle Link

When a cycle is running, an "Active Cycle" link appears in the navigation bar:
- Click to return to the active cycle monitoring page from anywhere
- Prevents starting conflicting cycles from other pages
- Disappears when cycle is stopped

---

## Database Viewer

View, analyze, and manage historical cycle data.

### Select a Cycle

**Cycle Dropdown**:
- Lists all saved cycles
- Format: Cycle name (date/time if auto-generated)
- Most recent cycles appear first

**Display Mode**:
Select what data to visualize:
- **Temperature**: Shows temperature sensor data only
- **Current**: Shows current/power measurements
- **Calculations**: Shows PID calculations, target temperature, errors
- **All Sensors**: Shows everything on one graph

### Actions

**Delete Data**:
- Deletes the currently selected cycle
- Confirmation dialog prevents accidental deletion
- Permanently removes data from database

**Delete All Data**:
- Deletes ALL cycles from the database
- **Warning**: This action cannot be undone
- Confirmation dialog required
- Use to free up storage space

**Export Data**:
- Exports selected cycle data to JSON file
- Downloads to your device
- File includes:
  - Cycle name and metadata
  - All sensor readings with timestamps
  - Calculation data (PID, errors, etc.)
- Can be imported later or analyzed externally

**Import Data**:
- Import previously exported cycle data
- Select JSON file from your device
- Validates data format before import
- Restores cycle to database
- **Note**: Cannot import if cycle name already exists

### Historical Graph

**Features**:
- Same visualization as real-time graph
- Shows complete cycle data
- Zoom and pan supported
- Reset Zoom button available

**Chart Controls**:
- **Reset Zoom**: Return to full cycle view
- **Drag to Zoom**: Select time range to zoom in
- **Double-click**: Alternative way to reset zoom

**Use Cases**:
- Analyze temperature control performance
- Compare heating vs cooling efficiency
- Identify temperature overshoot or oscillation
- Verify cycle completed as expected
- Export data for reports or analysis

---

## Configuration Editor

Advanced system configuration interface for editing JSON configuration files.

### File Selection

**Available Configuration Files**:
- `raspberry_pi_config.json` - Hardware pin mappings and sensor definitions
- `control_config.json` - PID parameters and control settings
- `graph_config.json` - Temperature profile constraints

**Select File**:
- Dropdown menu shows all `.json` files in config directory
- Select file to load its contents in the editor

### JSON Editor

**Interface**:
- Syntax-highlighted JSON editor
- Real-time validation
- Shows line numbers
- Auto-formatting

**Editing**:
1. Select configuration file from dropdown
2. Edit JSON directly in the editor
3. Syntax errors are highlighted
4. Click "Save Configuration"

**Validation**:
- JSON syntax is validated before saving
- Invalid JSON cannot be saved
- Error messages indicate the problem

### Configuration Types

#### raspberry_pi_config.json

Defines all hardware components and GPIO pins:

**Temperature Sensors**:
```json
{
  "Temperature_inside_top": {
    "name": "Temperature_inside_top",
    "type": "NTC",
    "editable": {
      "SDA": 2,
      "SCL": 3,
      "read_pin": 0,
      "i2c_address": "0x4A"
    }
  }
}
```

**Peltier Modules**:
```json
{
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

**⚠️ Important**: After changing GPIO pins, click the Restart button (🔄) in the navigation bar to restart the service.

#### control_config.json

PID controller parameters and safety limits:
- `Kp`, `Ki`, `Kd` - PID tuning constants
- `sample_time` - Control loop interval
- `output_limits` - Min/max PID output
- Safety thresholds

#### graph_config.json

Temperature profile constraints:
- `min_y`, `max_y` - Temperature range limits
- `max_rico` - Maximum rate of temperature change (°C/min)
- `max_rico_heating`, `max_rico_cooling` - Separate heating/cooling limits

### Save and Restart

**Save Configuration**:
- Validates JSON syntax
- Writes to configuration file
- Most changes reload automatically

**Restart Service Button** (in navigation bar):
- Required for GPIO pin changes
- Required for sensor type changes
- Restarts the entire Climate Chamber service
- System unavailable for 30-60 seconds

---

## Logs Viewer

System diagnostic logs for troubleshooting and monitoring.

### Log Structure

Logs are organized by:
- **Class Name**: Component that generated the log (e.g., ClimateChamber, SensorReader)
- **Run Timestamp**: Date and time when the log was created
- Format: `ClassName_YYYYMMDD_HHMMSS.log`

### Run Selection

**Available Runs**:
- Dropdown shows all log sessions
- Sorted by timestamp (newest first)
- Each run may have multiple class logs

**Select Run**:
- Choose a timestamp from dropdown
- All logs from that run are displayed

### Log Files Display

**Per Run**:
- Shows all class logs from selected run
- Each class has its own log file
- Click on a class name to view its log

**Class Logs**:
- Expandable sections for each class
- Click to view full log content
- Shows:
  - Initialization messages
  - Sensor readings
  - Control commands
  - Errors and warnings
  - Debug information

### Log Content

**Format**:
```
[ClassName] [method_name] Message text
```

**Example**:
```
[SensorReader] [read_sensors] Reading all sensors
[ClimateChamber] [apply_control] PID output: 45.3
[BTS7960Driver] [heat] HEATING - RPWM=45%, LPWM=0%
```

### Clear Logs

**Clear All Logs Button**:
- Deletes ALL log files and folders
- Frees up storage space
- Cannot be undone
- Confirmation dialog required

**When to Clear**:
- Storage space is low
- Old logs are no longer needed
- Fresh start for troubleshooting

**Logs Recreated**:
- New logs are automatically created on next run
- Each session gets a new timestamp

### Troubleshooting Use Cases

**Sensor Issues**:
- Check SensorReader logs
- Look for "None" values or read errors
- Verify I2C communication errors

**Peltier Control Issues**:
- Check ClimateChamber logs
- Review PID output values
- Check driver logs (BTS7960Driver, TB6612FNGDriver)

**Temperature Control Issues**:
- Review CalculationService logs
- Check PID error values
- Verify target vs current temperature

---

## Tips and Best Practices

### Starting a Temperature Cycle

1. **Check Current Temperature**: Always review starting temperature before creating a profile
2. **Enable Peltier Elements**: Don't forget to check the enable checkbox
3. **Monitor First Few Minutes**: Watch initial response to ensure system is working correctly
4. **Realistic Rates**: Don't expect extreme temperature changes (>5°C/min)

### Graph Design

1. **Start from Current**: First point should be close to current chamber temperature
2. **Gradual Changes**: Avoid sharp temperature jumps
3. **Test Profiles**: Try shorter cycles first to verify behavior
4. **Save Profiles**: Use Flow Designer to save and reuse complex sequences

### Data Management

1. **Regular Exports**: Export important cycle data before deleting
2. **Storage Monitoring**: Watch the storage indicator in navigation bar
3. **Clear Old Data**: Periodically delete unneeded cycles to free space
4. **Descriptive Names**: Use custom cycle names for important tests

### Safety

1. **Temperature Limits**: Respect configured min/max temperature ranges
2. **Monitor Actively**: Don't leave long cycles unattended initially
3. **Emergency Stop**: Stop cycle immediately if you observe unusual behavior
4. **Check Logs**: Review logs after any errors or unexpected behavior

### Performance

1. **Single Cycle**: Only run one cycle at a time
2. **Close Other Apps**: For best performance, close unnecessary browser tabs
3. **Network Stability**: Use wired Ethernet for most reliable connection
4. **Restart Service**: If system becomes unresponsive, use the Restart button

---

## Keyboard Shortcuts

- **Dark Mode**: Click moon icon in navigation bar
- **Active Cycle**: Automatically appears in nav bar when cycle is running
- **Browser Refresh**: F5 to reload page (may lose unsaved changes)

---

## Frequently Asked Questions

**Q: Why won't my Peltier elements activate?**
A: Ensure the "Enable Peltier Elements" checkbox is checked. This is a required safety feature.

**Q: Can I run multiple cycles simultaneously?**
A: No, only one cycle can run at a time. Stop the current cycle before starting a new one.

**Q: How do I save my temperature profile?**
A: Use the Temperature Flow Designer and click "Save Flow" to save complex sequences. Simple graphs are saved automatically when exported to server.

**Q: Why is my graph validation failing?**
A: The temperature change rate (rico) may exceed hardware capabilities. Try smaller temperature steps or longer time intervals.

**Q: How do I export my data?**
A: Use the Database Viewer, select your cycle, and click "Export Data". Data is saved as a JSON file.

**Q: What if the system becomes unresponsive?**
A: Click the Restart button (🔄) in the navigation bar to restart the service. If that fails, power cycle the Raspberry Pi.

**Q: Can I edit the configuration while a cycle is running?**
A: No, configuration editing is blocked during active cycles. Stop the cycle first.

**Q: How do I clear storage space?**
A: Delete old cycles in Database Viewer or clear logs in Logs Viewer.

---

---

**Document Version**: 1.1
**Last Updated**: 2025-10-02
