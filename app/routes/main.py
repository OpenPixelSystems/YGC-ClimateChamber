from flask import Blueprint, render_template, redirect, url_for, request, flash
from app import app_state
from app.backend.services.config import load_config, save_config
from app.backend.services.temperature import temperature_service

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return render_template('home.html')


@main_bp.route('/status')
def status():
    return 'Server is up and running', 200


@main_bp.route('/edit-config', methods=['GET', 'POST'])
def edit_config():
    if request.method == 'POST':
        try:
            new_config = {}
            for key, value in request.form.items():
                keys = key.split('.')
                current = new_config
                for k in keys[:-1]:
                    current = current.setdefault(k, {})
                current[keys[-1]] = try_convert(value)

            save_config(app_state.graph_config_path, new_config)
            flash('Configuration updated successfully!', 'success')
            
        except Exception as e:
            flash(f'Error updating configuration: {str(e)}', 'error')
            
        return redirect(url_for('main.edit_config'))

    config_data = load_config(app_state.graph_config_path)
    return render_template('configEditor.html', config=config_data)


@main_bp.route('/submit-temperature', methods=['POST'])
def submit_temperature():
    try:
        temperature = request.form['temperature']
        result = temperature_service.set_constant_temperature(temperature)
        
        if result.is_valid:
            flash(result.message, 'success')
            return redirect(url_for('graph.display_graph'))
        else:
            flash(result.message, 'error')
            return redirect(url_for('main.index'))
            
    except KeyError:
        flash('No temperature value provided', 'error')
        return redirect(url_for('main.index'))

@main_bp.route('/manual-control')
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