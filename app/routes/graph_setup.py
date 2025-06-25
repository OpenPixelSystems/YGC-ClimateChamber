from flask import Blueprint, render_template, jsonify, redirect, url_for, request

from app.backend.app_state import get_app_state

graph_bp = Blueprint('graph', __name__)

@graph_bp.route('/graph-setup')
def setup_graph():
    """Display the graph setup page"""
    return render_template('setupGraph.html')

@graph_bp.route('/store-graph-data', methods=['POST'])
def store_graph_data():
    """Process and store a new temperature profile"""
    try:
        graph_data = request.get_json()
        if not graph_data:
            return jsonify({"error": "No data received"}), 400

        # Process the temperature profile
        success, message, graph = get_app_state().temperature_service.set_temperature_profile(graph_data[0]['data'])
        
        if success:
            get_app_state().controller.desired_graph = graph
            return redirect(url_for('climate.display_graph'))
        else:
            return jsonify({"error": message}), 400

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@graph_bp.route('/get-stored-graph-data', methods=['GET'])
def get_stored_graph_data():
    """Get the current graph data for display"""
    config = get_app_state().config_manager.graph_config
    
    # Convert Graph object's setpoints to the format expected by frontend
    desired_path = None
    if get_app_state().controller.desired_graph:
        desired_path = [
            {"x": x, "y": y} 
            for x, y in get_app_state().controller.desired_flow_graph.setpoints
        ]
        
    return jsonify({
        'desired_path': desired_path,
        'config': {
            'max_rico': config.max_rico
        }
    })


@graph_bp.route('/get_graph_min_max_temp', methods=['GET'])
def get_graph_min_max_temp():
    """Get the current graph data for display"""
    config = get_app_state().config_manager.graph_config

    return jsonify({
        'min_temp': config.min_y,
        'max_temp': config.max_y
    })