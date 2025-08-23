from datetime import datetime

from flask import Blueprint, jsonify, Response, request, render_template
from app.backend.app_state import get_app_state

climate_bp = Blueprint('climate', __name__)

@climate_bp.route('/display-graph')
def display_graph():
    """Display the graph visualization page"""
    return render_template('displayGraph.html')

@climate_bp.route('/stream')
def stream():
    """Route that streams sensor data to the frontend using the ClimateChamberController instance."""
    app_state = get_app_state()
    app_state.controller.start_sensor_stream()  # Start the stream
    return Response(app_state.controller.sensor_data_provider(), mimetype='text/event-stream')

@climate_bp.route('/start-cycle', methods=['POST'])
def start_sensors(logging=True):
    """Start cycle should do following actions:
    - Set the desired graph.
    - Set the start timestamp.
    - Start the controlling cycle.
    - Accept optional custom cycle name.
    """
    # Get data from request
    data = request.get_json(silent=True) or {}
    custom_name = data.get('cycleName')

    app_state = get_app_state()
    app_state.start_time = datetime.now()
    if app_state.controller.desired_graph is not None:
        app_state.controller.set_start_time(datetime.now())
    if custom_name:
        cycle_name = custom_name
    else:
        cycle_name = "Temperature cycle " + datetime.now().strftime("%d%m%Y-%H:%M:%S")
    if logging:
        app_state.database.start_logging_cycle(cycle_name)
    app_state.controller.set_desired_graph(app_state.controller.desired_graph)

    return jsonify({"status": "success", "cycleName": cycle_name})

@climate_bp.route('/stop-cycle', methods=['POST'])
def stop_sensors():
    """Stop the sensor reading process."""
    app_state = get_app_state()
    app_state.controller.stop_sensor_stream()  # Stop the stream
    app_state.start_time = None
    app_state.database.stop_logging_cycle()
    return jsonify({'status': 'Sensors stopped'})

@climate_bp.route('/update-power', methods=['POST'])
def update_power():
    """Manually steer peltier power"""
    data = request.get_json(silent=True) or {}
    power_value = data.get('power')

    app_state = get_app_state()
    app_state.controller.manual_control(power_value)

    return jsonify({'status': 'Peltier power updated'})


@climate_bp.route('/enable_peltier', methods=['POST'])
def enable_peltier():
    """Enable/disable peltier elements"""
    data = request.get_json(silent=True) or {}
    enabled = data.get('enabled', False)

    app_state = get_app_state()

    if enabled:
        # Enable Peltier elements through the controller
        app_state.controller.enable_peltier_driver()
        status_message = 'Peltier elements enabled'
    else:
        # Disable Peltier elements through the controller
        app_state.controller.disable_peltier_driver()
        status_message = 'Peltier elements disabled'

    return jsonify({'status': status_message, 'enabled': enabled})

@climate_bp.route('/get-active-cycle-data', methods=['GET'])
def get_active_cycle_data():
    """Get data from the currently active cycle if one exists"""
    app_state = get_app_state()
    
    if not app_state.database.logging_active or not app_state.database.current_cycle_id:
        return jsonify({'active_cycle': False, 'data': None})
    
    # Get the current cycle name and start time
    with app_state.database.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, start_time FROM cycles WHERE cycle_id = ?", (app_state.database.current_cycle_id,))
        cycle_row = cursor.fetchone()
        cycle_name = cycle_row[0] if cycle_row else None
        cycle_start_time = cycle_row[1] if cycle_row else None
    
    if not cycle_name:
        return jsonify({'active_cycle': False, 'data': None})
    
    # Get the cycle data
    cycle_data = app_state.database.read_cycle_data(cycle_name)
    
    return jsonify({
        'active_cycle': True,
        'cycle_name': cycle_name,
        'cycle_id': app_state.database.current_cycle_id,
        'cycle_start_time': cycle_start_time,
        'data': cycle_data
    })