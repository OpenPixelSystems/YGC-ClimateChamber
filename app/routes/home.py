from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify

from app import get_app_state
from app.routes.Helper.graph import Graph

home_bp = Blueprint('home', __name__, template_folder='templates', static_folder='static')

@home_bp.route('/')
def index():
    # Check if there's an active cycle to determine button states
    app_state = get_app_state()
    active_cycle = app_state.database.logging_active
    return render_template('home.html', active_cycle=active_cycle)

@home_bp.route('/status')
def status():
    return 'Server is up and running', 200

@home_bp.route('/submit-temperature', methods=['POST'])
def submit_temperature():
    # Check if a cycle is already active
    app_state = get_app_state()
    if app_state.database.logging_active:
        flash('A cycle is already running. Stop the current cycle first.', 'error')
        return redirect(url_for('home.index'))
        
    try:
        temperature_str = request.form['temperature']

        result = get_app_state().temperature_service.set_constant_temperature(temperature_str)
        get_app_state().controller.set_desired_graph(
            Graph("desired_graph", [(0, float(temperature_str))], get_app_state().config_manager))

        if result.is_valid:
            flash(result.message, 'success')
            return redirect(url_for('climate.display_graph'))
        else:
            flash(result.message, 'error')
            return redirect(url_for('home.index'))
            
    except KeyError:
        flash('No temperature value provided', 'error')
        return redirect(url_for('home.index'))

@home_bp.route('/manual-control')
def manual_control():
    # Check if a cycle is already active from a different page
    app_state = get_app_state()
    if app_state.database.logging_active:
        with app_state.database.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT origin_page FROM cycles WHERE cycle_id = ?", (app_state.database.current_cycle_id,))
            cycle_row = cursor.fetchone()
            origin_page = cycle_row[0] if cycle_row else None
            
            # Only block if cycle was started from a different page
            if origin_page and origin_page != 'manual-control':
                flash('A cycle is already running from a different page. Use the Active Cycle button to access it.', 'error')
                return redirect(url_for('home.index'))
    
    return render_template('manualControl.html')

def try_convert(value):
    """Convert string values to appropriate numeric types if possible"""
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value