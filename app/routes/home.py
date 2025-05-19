from flask import Blueprint, render_template, redirect, url_for, request, flash

from app import get_app_state
from app.backend.graph import Graph

home_bp = Blueprint('home', __name__, template_folder='templates', static_folder='static')

@home_bp.route('/')
def index():
    return render_template('home.html')

@home_bp.route('/status')
def status():
    return 'Server is up and running', 200

@home_bp.route('/submit-temperature', methods=['POST'])
def submit_temperature():
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