from flask import Blueprint, render_template, jsonify, redirect, url_for, request

from app.backend.services.config import load_config
from app import app_state
from app.backend.services.temperature import temperature_service

graph_bp = Blueprint('graph', __name__)

@graph_bp.route('/setup-graph')
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
        success, message, graph = temperature_service.set_temperature_profile(graph_data[0]['data'])
        
        if success:
            app_state.desired_flow_graph = graph
            return redirect(url_for('graph.display_graph'))
        else:
            return jsonify({"error": message}), 400

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@graph_bp.route('/display-graph')
def display_graph():
    """Display the graph visualization page"""
    return render_template('displayGraph.html')

@graph_bp.route('/get-stored-graph-data', methods=['GET'])
def get_stored_graph_data():
    """Get the current graph data for display"""
    config = load_config(app_state.graph_config_path)
    
    # Convert Graph object's setpoints to the format expected by frontend
    desired_path = None
    if app_state.desired_flow_graph:
        desired_path = [
            {"x": x, "y": y} 
            for x, y in app_state.desired_flow_graph.setpoints
        ]
        
    return jsonify({
        'desired_path': desired_path,
        'config': {
            'max_rico': config.get('max_rico', {}).get('value')
        }
    })