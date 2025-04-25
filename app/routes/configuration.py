from flask import Blueprint, render_template, redirect, url_for, request, flash
from app import app_state
from app.backend.services.config import load_config, save_config

config_bp = Blueprint('config', __name__)

@config_bp.route('/edit-config', methods=['GET', 'POST'])
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

        return redirect(url_for('config.edit_config'))

    config_data = load_config(app_state.graph_config_path)
    return render_template('configEditor.html', config=config_data)

def try_convert(value):
    """Convert string values to appropriate numeric types if possible"""
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value