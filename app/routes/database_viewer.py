from flask import Blueprint, render_template, jsonify
import sqlite3

from app import app_state


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
    cycles = app_state.database.list_cycle_names()
    return jsonify(cycles)

#TODO Edit query to fetch all data from given cycle name
@viewer_bp.route('/api/data/<int:cycle_id>')
def get_cycle_data(cycle_id):
    conn = get_db_connection()
    readings = conn.execute(
        'SELECT timestamp, sensor_id, temperature FROM sensor_readings WHERE cycle_id = ?',
        (cycle_id,)
    ).fetchall()
    conn.close()
    return jsonify([dict(row) for row in readings])