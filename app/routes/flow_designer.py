from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
import json
import os
import time
from pathlib import Path

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
    """Store temperature flow data for execution"""
    try:
        flow_data = request.get_json()
        if not flow_data:
            return jsonify({"error": "No flow data received"}), 400

        # Validate required data structure
        if 'fullFlowData' not in flow_data or 'executionFlow' not in flow_data:
            return jsonify({"error": "Invalid flow data format"}), 400

        execution_flow = flow_data['executionFlow']
        full_flow = flow_data['fullFlowData']

        # Validate execution flow structure
        if 'executionSteps' not in execution_flow or 'metadata' not in execution_flow:
            return jsonify({"error": "Invalid execution flow structure"}), 400

        # Store flow data for execution
        app_state = get_app_state()
        app_state.execution_flow = execution_flow
        app_state.full_flow_data = full_flow

        return jsonify({
            "success": True,
            "message": "Flow exported to server successfully",
            "flowId": execution_flow.get('flowId'),
            "totalSteps": execution_flow['metadata'].get('totalSteps'),
            "estimatedDuration": execution_flow['metadata'].get('estimatedDurationMinutes')
        })

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

@flow_bp.route('/get-execution-flow', methods=['GET'])
def get_execution_flow():
    """Get the stored execution flow data"""
    try:
        app_state = get_app_state()

        # Check if execution flow exists
        if hasattr(app_state, 'execution_flow'):
            return jsonify({
                "success": True,
                "executionFlow": app_state.execution_flow
            })
        else:
            return jsonify({
                "success": False,
                "error": "No execution flow found"
            }), 404

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@flow_bp.route('/save-flow-diagram', methods=['POST'])
def save_flow_diagram():
    """Save a flow diagram with a name"""
    try:
        flow_data = request.get_json()
        if not flow_data:
            return jsonify({"error": "No flow data received"}), 400

        if 'name' not in flow_data:
            return jsonify({"error": "Flow name is required"}), 400


        # Create flows directory if it doesn't exist
        flows_dir = Path('app/backend/saved_flows')
        flows_dir.mkdir(exist_ok=True)

        # Generate unique ID for the flow
        flow_id = f"flow_{int(flow_data.get('created', '').replace('-', '').replace(':', '').replace('.', '').replace('T', '').replace('Z', '')[:14]) or int(time.time() * 1000)}"

        # Add ID to flow data
        flow_data['id'] = flow_id

        # Save flow to file
        flow_file = flows_dir / f"{flow_id}.json"
        with open(flow_file, 'w') as f:
            json.dump(flow_data, f, indent=2)

        return jsonify({
            "success": True,
            "message": f"Flow '{flow_data['name']}' saved successfully",
            "flowId": flow_id
        })

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@flow_bp.route('/get-saved-flows', methods=['GET'])
def get_saved_flows():
    """Get list of all saved flow diagrams"""
    try:

        flows_dir = Path('app/backend/saved_flows')
        flows = []

        if flows_dir.exists():
            for flow_file in flows_dir.glob('*.json'):
                try:
                    with open(flow_file, 'r') as f:
                        flow_data = json.load(f)

                        # Extract summary information
                        flows.append({
                            'id': flow_data.get('id', flow_file.stem),
                            'name': flow_data.get('name', 'Unnamed Flow'),
                            'created': flow_data.get('created'),
                            'lastModified': flow_data.get('lastModified', flow_data.get('created')),
                            'metadata': flow_data.get('metadata', {})
                        })
                except Exception as e:
                    print(f"Error reading flow file {flow_file}: {e}")
                    continue

        # Sort by last modified date (newest first)
        flows.sort(key=lambda x: x.get('lastModified', ''), reverse=True)

        return jsonify({
            "success": True,
            "flows": flows
        })

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@flow_bp.route('/get-flow-diagram/<flow_id>', methods=['GET'])
def get_flow_diagram(flow_id):
    """Get a specific flow diagram by ID"""
    try:

        flows_dir = Path('app/backend/saved_flows')
        flow_file = flows_dir / f"{flow_id}.json"

        if not flow_file.exists():
            return jsonify({"error": "Flow not found"}), 404

        with open(flow_file, 'r') as f:
            flow_data = json.load(f)

        return jsonify({
            "success": True,
            "flowData": flow_data
        })

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@flow_bp.route('/delete-flow-diagram/<flow_id>', methods=['DELETE'])
def delete_flow_diagram(flow_id):
    """Delete a flow diagram by ID"""
    try:

        flows_dir = Path('app/backend/saved_flows')
        flow_file = flows_dir / f"{flow_id}.json"

        if not flow_file.exists():
            return jsonify({"error": "Flow not found"}), 404

        # Get flow name before deletion for response
        with open(flow_file, 'r') as f:
            flow_data = json.load(f)
            flow_name = flow_data.get('name', 'Unknown')

        # Delete the file
        os.remove(flow_file)

        return jsonify({
            "success": True,
            "message": f"Flow '{flow_name}' deleted successfully"
        })

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500