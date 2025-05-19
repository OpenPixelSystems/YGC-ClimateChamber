from flask import Blueprint, render_template, jsonify

from app.backend.app_state import get_app_state

viewer_bp = Blueprint('viewer', __name__)

@viewer_bp.route('/view-database')
def view_database():
    return render_template('databaseViewer.html')

@viewer_bp.route('/api/cycles')
def get_cycles():
    cycles = get_app_state().database.list_cycle_names()
    return jsonify(cycles)

@viewer_bp.route('/api/delete_cycle/<cycle_name>')
def delete_cycle(cycle_name):
    success = get_app_state().database.delete_cycle(cycle_name)
    if success:
        result = {"status": "success", "message": "Action performed"}
        return jsonify(result), 200  # HTTP 200 OK
    else:
        result = {"status": "error", "message": "No cycle with name = "+cycle_name}
        return jsonify(result), 500  # Internal Server Error
    

@viewer_bp.route('/api/data/<cycle_name>')
def get_cycle_data(cycle_name):
    readings = get_app_state().database.read_cycle_data(cycle_name)
    return jsonify(readings)