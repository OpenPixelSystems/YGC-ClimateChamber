from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
import json
import os
import time
from pathlib import Path

from app.backend.app_state import get_app_state
from app.backend.FlowExecution.FlowExecutor import FlowExecutor

flow_bp = Blueprint("flow", __name__)


@flow_bp.route("/flow-designer")
def flow_designer():
    """Display the temperature flow designer page"""
    # Check if a cycle is already active
    app_state = get_app_state()
    if app_state.database.logging_active:
        flash(
            "Cannot edit flow while a cycle is running. Stop the current cycle first.",
            "error",
        )
        return redirect(url_for("home.index"))
    return render_template("flow_designer.html")


@flow_bp.route("/flow-execution")
def flow_execution():
    """Display the flow execution page"""
    app_state = get_app_state()

    # Check if there's a flow ready for execution
    if not hasattr(app_state, "flow_executor") or not app_state.flow_executor:
        flash(
            "No flow loaded for execution. Please design and export a flow first.",
            "error",
        )
        return redirect(url_for("flow.flow_designer"))

    # Check if a cycle is already active and it's not a flow execution cycle
    if app_state.database.logging_active:
        # Get the current cycle's origin page to check if it's a flow execution cycle
        with app_state.database.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT origin_page FROM cycles WHERE cycle_id = ?",
                (app_state.database.current_cycle_id,),
            )
            cycle_row = cursor.fetchone()
            origin_page = cycle_row[0] if cycle_row else None

        # Only redirect if it's not a flow execution cycle
        if origin_page != "flow-execution":
            flash(
                "Cannot start flow execution while a cycle is running. Stop the current cycle first.",
                "error",
            )
            return redirect(url_for("home.index"))

    return render_template("flow_execution.html")


@flow_bp.route("/store-flow-data", methods=["POST"])
def store_flow_data():
    """Store temperature flow data for execution"""
    try:
        flow_data = request.get_json()
        if not flow_data:
            return jsonify({"error": "No flow data received"}), 400

        # Validate required data structure
        if "fullFlowData" not in flow_data or "executionFlow" not in flow_data:
            return jsonify({"error": "Invalid flow data format"}), 400

        execution_flow = flow_data["executionFlow"]
        full_flow = flow_data["fullFlowData"]

        # Validate execution flow structure
        if "executionSteps" not in execution_flow or "metadata" not in execution_flow:
            return jsonify({"error": "Invalid execution flow structure"}), 400

        # Create FlowExecutor and store in app_state
        app_state = get_app_state()
        flow_executor = FlowExecutor(execution_flow, full_flow)
        app_state.flow_executor = flow_executor

        return jsonify(
            {
                "success": True,
                "message": "Flow exported to server successfully",
                "redirectTo": "/flow-execution",
                "flowId": execution_flow.get("flowId"),
                "totalSteps": execution_flow["metadata"].get("totalSteps"),
                "estimatedDuration": execution_flow["metadata"].get(
                    "estimatedDurationMinutes"
                ),
            }
        )

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@flow_bp.route("/get-flow-config", methods=["GET"])
def get_flow_config():
    """Get flow configuration limits"""
    config = get_app_state().config_manager.graph_config

    return jsonify(
        {
            "min_temp": config.min_y,
            "max_temp": config.max_y,
            "max_hold_time": 1440,  # 24 hours in minutes
            "max_rico_heating": config.max_rico_heating,
            "max_rico_cooling": config.max_rico_cooling,
            "heating_curve_factor": config.heating_curve_factor,
            "cooling_curve_factor": config.cooling_curve_factor,
        }
    )


@flow_bp.route("/get-current-chamber-temperature", methods=["GET"])
def get_current_chamber_temperature():
    """Get current average temperature inside the climate chamber"""
    try:
        app_state = get_app_state()

        # Get current sensor readings
        sensor_data = app_state.controller.sensor_reader.read_sensors()

        # Calculate average of inside temperatures
        inside_temps = []
        for sensor_name, value in sensor_data.items():
            # Skip metadata entries
            if sensor_name.startswith("_"):
                continue

            # Handle nested dict structure {sensor_name: {'sensor_value': x, 'sensor_source': y}}
            if isinstance(value, dict):
                temp_value = value.get("sensor_value")
            else:
                temp_value = value

            if "inside" in sensor_name.lower() and temp_value is not None:
                inside_temps.append(temp_value)

        if inside_temps:
            avg_temp = sum(inside_temps) / len(inside_temps)
            return jsonify(
                {
                    "success": True,
                    "temperature": round(avg_temp, 2),
                    "sensor_count": len(inside_temps),
                }
            )
        else:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "No inside temperature sensors available",
                    }
                ),
                404,
            )

    except Exception as e:
        import traceback

        print(f"[get_current_chamber_temperature] Error: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"success": False, "error": f"An error occurred: {str(e)}"}), 500


@flow_bp.route("/get-execution-flow", methods=["GET"])
def get_execution_flow():
    """Get the stored execution flow data"""
    try:
        app_state = get_app_state()

        # Check if FlowExecutor exists
        if hasattr(app_state, "flow_executor") and app_state.flow_executor:
            return jsonify(
                {
                    "success": True,
                    "executionFlow": app_state.flow_executor.execution_flow,
                    "status": app_state.flow_executor.get_execution_status(),
                }
            )
        else:
            return jsonify({"success": False, "error": "No execution flow found"}), 404

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@flow_bp.route("/start-flow-execution", methods=["POST"])
def start_flow_execution():
    """Start executing the stored flow"""
    try:
        app_state = get_app_state()

        if not hasattr(app_state, "flow_executor") or not app_state.flow_executor:
            return jsonify({"error": "No flow loaded for execution"}), 400

        # Check if a cycle is already running
        if app_state.database.logging_active:
            return jsonify({"error": "A cycle is already running"}), 400

        # Get request data for custom cycle name
        data = request.get_json(silent=True) or {}
        custom_name = data.get("cycleName")

        # Set start time
        from datetime import datetime

        app_state.start_time = datetime.now()

        # Generate cycle name
        if custom_name:
            cycle_name = custom_name
        else:
            flow_id = app_state.flow_executor.execution_flow.get("flowId", "Flow")
            cycle_name = f"Flow Execution - {flow_id} - " + datetime.now().strftime(
                "%d%m%Y-%H:%M:%S"
            )

        # Start database logging for flow execution
        app_state.database.start_logging_cycle(cycle_name, "flow-execution")

        # Start flow execution
        app_state.flow_executor.start_execution()

        # Set flow executor in controller for flow-based control
        app_state.controller.set_flow_executor(app_state.flow_executor)

        # Enable Peltier elements for flow execution
        app_state.controller.enable_peltier_driver()

        # Start sensor reading in background
        app_state.controller.start_sensor_stream()

        return jsonify(
            {
                "success": True,
                "message": "Flow execution started",
                "cycleName": cycle_name,
                "status": app_state.flow_executor.get_execution_status(),
            }
        )

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@flow_bp.route("/stop-flow-execution", methods=["POST"])
def stop_flow_execution():
    """Stop flow execution"""
    try:
        app_state = get_app_state()

        if not hasattr(app_state, "flow_executor") or not app_state.flow_executor:
            return jsonify({"error": "No flow loaded"}), 400

        # Stop flow execution
        app_state.flow_executor.stop_execution()

        # Clear flow executor from controller
        app_state.controller.set_flow_executor(None)

        # Disable Peltier elements when stopping flow execution
        app_state.controller.disable_peltier_driver()

        # Stop database logging if active
        if app_state.database.logging_active:
            app_state.database.stop_logging_cycle()

        # Stop sensor stream
        app_state.controller.stop_sensor_stream()

        return jsonify(
            {
                "success": True,
                "message": "Flow execution stopped",
                "status": app_state.flow_executor.get_execution_status(),
            }
        )

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@flow_bp.route("/get-flow-execution-status", methods=["GET"])
def get_flow_execution_status():
    """Get current flow execution status"""
    try:
        app_state = get_app_state()

        if not hasattr(app_state, "flow_executor") or not app_state.flow_executor:
            return jsonify({"success": False, "error": "No flow loaded"}), 404

        return jsonify(
            {"success": True, "status": app_state.flow_executor.get_execution_status()}
        )

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@flow_bp.route("/save-flow-diagram", methods=["POST"])
def save_flow_diagram():
    """Save a flow diagram with a name"""
    try:
        flow_data = request.get_json()
        if not flow_data:
            return jsonify({"error": "No flow data received"}), 400

        if "name" not in flow_data:
            return jsonify({"error": "Flow name is required"}), 400

        # Create flows directory if it doesn't exist
        flows_dir = Path("app/backend/saved_flows")
        flows_dir.mkdir(exist_ok=True)

        # Generate unique ID for the flow
        flow_id = f"flow_{int(flow_data.get('created', '').replace('-', '').replace(':', '').replace('.', '').replace('T', '').replace('Z', '')[:14]) or int(time.time() * 1000)}"

        # Add ID to flow data
        flow_data["id"] = flow_id

        # Save flow to file
        flow_file = flows_dir / f"{flow_id}.json"
        with open(flow_file, "w") as f:
            json.dump(flow_data, f, indent=2)

        return jsonify(
            {
                "success": True,
                "message": f"Flow '{flow_data['name']}' saved successfully",
                "flowId": flow_id,
            }
        )

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@flow_bp.route("/get-saved-flows", methods=["GET"])
def get_saved_flows():
    """Get list of all saved flow diagrams"""
    try:

        flows_dir = Path("app/backend/saved_flows")
        flows = []

        if flows_dir.exists():
            for flow_file in flows_dir.glob("*.json"):
                try:
                    with open(flow_file, "r") as f:
                        flow_data = json.load(f)

                        # Extract summary information
                        flows.append(
                            {
                                "id": flow_data.get("id", flow_file.stem),
                                "name": flow_data.get("name", "Unnamed Flow"),
                                "created": flow_data.get("created"),
                                "lastModified": flow_data.get(
                                    "lastModified", flow_data.get("created")
                                ),
                                "metadata": flow_data.get("metadata", {}),
                            }
                        )
                except Exception as e:
                    print(f"Error reading flow file {flow_file}: {e}")
                    continue

        # Sort by last modified date (newest first)
        flows.sort(key=lambda x: x.get("lastModified", ""), reverse=True)

        return jsonify({"success": True, "flows": flows})

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@flow_bp.route("/get-flow-diagram/<flow_id>", methods=["GET"])
def get_flow_diagram(flow_id):
    """Get a specific flow diagram by ID"""
    try:

        flows_dir = Path("app/backend/saved_flows")
        flow_file = flows_dir / f"{flow_id}.json"

        if not flow_file.exists():
            return jsonify({"error": "Flow not found"}), 404

        with open(flow_file, "r") as f:
            flow_data = json.load(f)

        return jsonify({"success": True, "flowData": flow_data})

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@flow_bp.route("/delete-flow-diagram/<flow_id>", methods=["DELETE"])
def delete_flow_diagram(flow_id):
    """Delete a flow diagram by ID"""
    try:

        flows_dir = Path("app/backend/saved_flows")
        flow_file = flows_dir / f"{flow_id}.json"

        if not flow_file.exists():
            return jsonify({"error": "Flow not found"}), 404

        # Get flow name before deletion for response
        with open(flow_file, "r") as f:
            flow_data = json.load(f)
            flow_name = flow_data.get("name", "Unknown")

        # Delete the file
        os.remove(flow_file)

        return jsonify(
            {"success": True, "message": f"Flow '{flow_name}' deleted successfully"}
        )

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500
