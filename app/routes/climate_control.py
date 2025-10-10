from datetime import datetime

from flask import (
    Blueprint,
    jsonify,
    Response,
    request,
    render_template,
    flash,
    redirect,
    url_for,
)
from app.backend.app_state import get_app_state

climate_bp = Blueprint("climate", __name__)


@climate_bp.route("/display-graph")
def display_graph():
    """Display the graph visualization page"""
    app_state = get_app_state()

    # Check if there's an active cycle from a different page
    if app_state.database.logging_active:
        with app_state.database.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT origin_page FROM cycles WHERE cycle_id = ?",
                (app_state.database.current_cycle_id,),
            )
            cycle_row = cursor.fetchone()
            origin_page = cycle_row[0] if cycle_row else None

            # Only block if cycle was started from a different page
            if origin_page and origin_page != "display-graph":
                flash(
                    "A cycle is already running from a different page. Use the Active Cycle button to access it.",
                    "error",
                )
                return redirect(url_for("home.index"))

    return render_template("displayGraph.html")


@climate_bp.route("/stream")
def stream():
    """Route that streams sensor data to the frontend using the ClimateChamberController instance."""
    app_state = get_app_state()
    # Only start sensor stream if not already running
    if not app_state.controller.running:
        app_state.controller.start_sensor_stream()
    return Response(
        app_state.controller.sensor_data_provider(), mimetype="text/event-stream"
    )


@climate_bp.route("/start-cycle", methods=["POST"])
def start_sensors(logging=True):
    """Start cycle should do following actions:
    - Set the desired graph.
    - Set the start timestamp.
    - Start the controlling cycle.
    - Start sensor reading and steering in background.
    - Accept optional custom cycle name.
    """
    app_state = get_app_state()

    # Check if a cycle is already running
    if app_state.database.logging_active:
        return (
            jsonify({"status": "error", "message": "A cycle is already running"}),
            400,
        )

    # Get data from request
    data = request.get_json(silent=True) or {}
    custom_name = data.get("cycleName")
    origin_page = data.get("originPage", "unknown")

    app_state.start_time = datetime.now()
    if app_state.controller.desired_graph is not None:
        app_state.controller.set_start_time(datetime.now())
    if custom_name:
        cycle_name = custom_name
    else:
        cycle_name = "Temperature cycle " + datetime.now().strftime("%d%m%Y-%H:%M:%S")

    # Start database logging
    if logging:
        app_state.database.start_logging_cycle(cycle_name, origin_page)

    # Set the desired graph for control
    app_state.controller.set_desired_graph(app_state.controller.desired_graph)

    # Start sensor reading and steering in background
    app_state.controller.start_sensor_stream()

    return jsonify({"status": "success", "cycleName": cycle_name})


@climate_bp.route("/stop-cycle", methods=["POST"])
def stop_sensors():
    """Stop the sensor reading process."""
    app_state = get_app_state()
    app_state.controller.stop_sensor_stream()  # Stop the stream
    app_state.start_time = None
    app_state.database.stop_logging_cycle()
    return jsonify({"status": "Sensors stopped"})


@climate_bp.route("/update-power", methods=["POST"])
def update_power():
    """Manually steer peltier power"""
    data = request.get_json(silent=True) or {}
    power_value = data.get("power")

    app_state = get_app_state()
    app_state.controller.manual_control(power_value)

    return jsonify({"status": "Peltier power updated"})


@climate_bp.route("/enable_peltier", methods=["POST"])
def enable_peltier():
    """Enable/disable peltier elements"""
    data = request.get_json(silent=True) or {}
    enabled = data.get("enabled", False)

    app_state = get_app_state()

    if enabled:
        # Enable Peltier elements through the controller
        app_state.controller.enable_peltier_driver()
        status_message = "Peltier elements enabled"
    else:
        # Disable Peltier elements through the controller
        app_state.controller.disable_peltier_driver()
        status_message = "Peltier elements disabled"

    return jsonify({"status": status_message, "enabled": enabled})


@climate_bp.route("/get-active-cycle-data", methods=["GET"])
def get_active_cycle_data():
    """Get data from the currently active cycle if one exists"""
    app_state = get_app_state()

    if not app_state.database.logging_active or not app_state.database.current_cycle_id:
        return jsonify({"active_cycle": False, "data": None})

    # Get the current cycle name, start time, and origin page
    with app_state.database.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name, start_time, origin_page FROM cycles WHERE cycle_id = ?",
            (app_state.database.current_cycle_id,),
        )
        cycle_row = cursor.fetchone()
        cycle_name = cycle_row[0] if cycle_row else None
        cycle_start_time = cycle_row[1] if cycle_row else None
        origin_page = (
            cycle_row[2] if cycle_row and len(cycle_row) > 2 else "display-graph"
        )

    if not cycle_name:
        return jsonify({"active_cycle": False, "data": None})

    # Get the cycle data
    cycle_data = app_state.database.read_cycle_data(cycle_name)

    return jsonify(
        {
            "active_cycle": True,
            "cycle_name": cycle_name,
            "cycle_id": app_state.database.current_cycle_id,
            "cycle_start_time": cycle_start_time,
            "origin_page": origin_page,
            "data": cycle_data,
        }
    )


@climate_bp.route("/clear-graph-if-needed", methods=["POST"])
def clear_graph_if_needed():
    """Clear desired graph if cycle is stopped and page is being unloaded"""
    app_state = get_app_state()

    # Only clear if no cycle is running
    if not app_state.database.logging_active:
        app_state.controller.desired_graph = None
        return jsonify({"status": "Graph cleared"})

    return jsonify({"status": "Graph preserved - cycle active"})
