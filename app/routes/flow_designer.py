from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for

from app.backend.app_state import get_app_state

flow_bp = Blueprint('flow', __name__)

@flow_bp.route('/flow-designer')
def flow_designer():
    """Display the temperature flow designer page"""
    # Check if a cycle is already active
    app_state = get_app_state()
    if app_state.database.logging_active:
        flash('Cannot edit flow while a cycle is running. Stop the current cycle first.', 'error')
        return redirect(url_for('home.index'))
    return render_template('flow_designer.html')

@flow_bp.route('/store-flow-data', methods=['POST'])
def store_flow_data():
    """Process and store a new temperature flow"""
    try:
        flow_data = request.get_json()
        if not flow_data:
            return jsonify({"error": "No flow data received"}), 400

        # Validate flow structure
        if 'nodes' not in flow_data or 'connections' not in flow_data:
            return jsonify({"error": "Invalid flow data structure"}), 400

        # Store flow data for future processing
        app_state = get_app_state()
        setattr(app_state, 'temperature_flow', flow_data)

        return jsonify({"success": True, "message": "Flow stored successfully"})

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@flow_bp.route('/get-flow-config', methods=['GET'])
def get_flow_config():
    """Get flow configuration limits"""
    config = get_app_state().config_manager.graph_config

    return jsonify({
        'min_temp': config.min_y,
        'max_temp': config.max_y,
        'max_hold_time': 1440  # 24 hours in minutes
    })