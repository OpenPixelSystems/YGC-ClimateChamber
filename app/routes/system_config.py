from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from app.backend.app_state import get_app_state
from app.routes.Helper.config import load_config, save_config
import os

#TODO move config logic to config_manager

CONFIG_DIR = os.path.join(os.path.dirname(__file__), '../backend/config')
config_bp = Blueprint('config', __name__, template_folder='templates', static_folder='static')

def list_config_files():
    # List all .json config files in the config directory
    files = []
    for fname in os.listdir(CONFIG_DIR):
        if fname.endswith('.json'):
            files.append(fname)
    return files

@config_bp.route('/list-config-files', methods=['GET'])
def list_config_files_api():
    files = list_config_files()
    return jsonify({'files': files})

@config_bp.route('/api/get-config', methods=['GET'])
def api_get_config():
    filename = request.args.get('filename')
    if not filename:
        return jsonify({'error': 'No filename provided'}), 400
    config_path = os.path.join(CONFIG_DIR, filename)
    try:
        config_data = load_config(config_path)
        return jsonify({'config': config_data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@config_bp.route('/api/save-config', methods=['POST'])
def api_save_config():
    data = request.get_json()
    filename = data.get('filename')
    config_data = data.get('config')
    if not filename or config_data is None:
        return jsonify({'error': 'Missing filename or config'}), 400
    config_path = os.path.join(CONFIG_DIR, filename)
    try:
        save_config(config_path, config_data)
        get_app_state().reload_climate_chamber()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@config_bp.route('/restart-service', methods=['POST'])
def restart_service():
    try:
        get_app_state().restart_climate_chamber_service()
        return jsonify({'success': True, 'message': 'Service restart initiated'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@config_bp.route('/edit-config', methods=['GET', 'POST'])
def edit_config():
    # Get filename from query or form
    filename = request.args.get('filename') if request.method == 'GET' else request.form.get('filename')
    if not filename:
        # Default to graph_config.json if not specified
        filename = 'graph_config.json'
    config_path = os.path.join(CONFIG_DIR, filename)

    if request.method == 'POST':
        try:
            new_config = {}
            for key, value in request.form.items():
                if key == 'filename':
                    continue
                keys = key.split('.')
                current = new_config
                for k in keys[:-1]:
                    current = current.setdefault(k, {})
                current[keys[-1]] = try_convert(value)

            save_config(config_path, new_config)
            flash(f'Configuration for {filename} updated successfully!', 'success')
        except Exception as e:
            flash(f'Error updating configuration: {str(e)}', 'error')
        return redirect(url_for('config.edit_config', filename=filename))

    # GET
    try:
        config_data = load_config(config_path)
    except Exception as e:
        config_data = {}
        flash(f'Error loading configuration: {str(e)}', 'error')
    files = list_config_files()
    return render_template('configEditor.html', config=config_data, config_files=files, selected_file=filename)

def try_convert(value):
    """Convert string values to appropriate numeric types if possible"""
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value