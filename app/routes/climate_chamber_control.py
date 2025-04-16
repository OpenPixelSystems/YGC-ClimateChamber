from datetime import datetime

from flask import Blueprint, jsonify, Response, request
from app import app_state

sensor_bp = Blueprint('sensor', __name__)

@sensor_bp.route('/stream')
def stream():
    """Route that streams sensor data to the frontend using the ClimateChamberController instance."""
    app_state.controller.start_sensor_stream()  # Start the stream
    #TODO stream is currently fed by sensor file, either feed real time sensor data into file or rework functionality
    return Response(app_state.controller.sensor_data_provider(), mimetype='text/event-stream')


@sensor_bp.route('/start_cycle', methods=['POST'])
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

    app_state.start_time = datetime.now()
    if logging:
        if custom_name:
            cycle_name = custom_name
        else:
            cycle_name = "Temperature cycle " + app_state.start_time.strftime("%d%m%Y-%H:%M:%S")
        print(cycle_name)
        app_state.database.start_logging_cycle(cycle_name)
    app_state.controller.set_desired_graph(app_state.desired_flow_graph)

    return jsonify({"status": "success", "cycleName": cycle_name})

@sensor_bp.route('/stop_cycle', methods=['POST'])
def stop_sensors():
    """Stop the sensor reading process."""
    app_state.controller.stop_sensor_stream()  # Stop the stream
    app_state.start_time = None
    app_state.database.stop_logging_cycle()
    return jsonify({'status': 'sensors stopped'})