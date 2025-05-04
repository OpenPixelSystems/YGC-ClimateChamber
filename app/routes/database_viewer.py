from flask import Blueprint, render_template, jsonify
import sqlite3

from app.backend.services.app_state import get_app_state

viewer_bp = Blueprint('viewer', __name__, template_folder='templates', static_folder='static')

def get_db_connection():
    conn = sqlite3.connect('ClimateChamber_data.db')
    conn.row_factory = sqlite3.Row
    return conn

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