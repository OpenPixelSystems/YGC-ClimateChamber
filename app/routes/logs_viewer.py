import os
import re
from datetime import datetime
from flask import Blueprint, render_template, jsonify, request
from pathlib import Path

logs_bp = Blueprint('logs', __name__, template_folder='templates', static_folder='static')

def get_log_directory():
    """Get the logs directory path"""
    return Path(__file__).parent.parent.parent / 'logs'

def parse_log_filename(filename):
    """Parse log filename to extract classname and datetime"""
    pattern = r'^(\w+)_(\d{8})_(\d{6})\.log$'
    match = re.match(pattern, filename)
    if match:
        classname, date_str, time_str = match.groups()
        datetime_str = f"{date_str}_{time_str}"
        try:
            parsed_datetime = datetime.strptime(datetime_str, "%Y%m%d_%H%M%S")
            return {
                'classname': classname,
                'datetime': parsed_datetime,
                'datetime_str': datetime_str,
                'filename': filename
            }
        except ValueError:
            return None
    return None

def get_available_runs():
    """Get all available log runs grouped by datetime"""
    log_dir = get_log_directory()
    if not log_dir.exists():
        return []
    
    runs = {}
    
    for subdir in log_dir.iterdir():
        if subdir.is_dir():
            classname = subdir.name
            for log_file in subdir.glob("*.log"):
                parsed = parse_log_filename(log_file.name)
                if parsed:
                    datetime_str = parsed['datetime_str']
                    if datetime_str not in runs:
                        runs[datetime_str] = {
                            'datetime': parsed['datetime'],
                            'datetime_str': datetime_str,
                            'logs': []
                        }
                    runs[datetime_str]['logs'].append({
                        'classname': classname,
                        'filename': log_file.name,
                        'path': str(log_file)
                    })
    
    # Sort runs by datetime (newest first)
    sorted_runs = sorted(runs.values(), key=lambda x: x['datetime'], reverse=True)
    
    # Sort logs within each run by classname
    for run in sorted_runs:
        run['logs'].sort(key=lambda x: x['classname'])
    
    return sorted_runs

@logs_bp.route('/logs')
def logs_viewer():
    """Main logs viewer page"""
    return render_template('logs_viewer.html')

@logs_bp.route('/api/logs/runs')
def api_get_runs():
    """API endpoint to get available log runs"""
    try:
        runs = get_available_runs()
        # Convert datetime objects to strings for JSON serialization
        for run in runs:
            run['datetime'] = run['datetime'].strftime('%Y-%m-%d %H:%M:%S')
        return jsonify(runs)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@logs_bp.route('/api/logs/content')
def api_get_log_content():
    """API endpoint to get log file content"""
    classname = request.args.get('classname')
    datetime_str = request.args.get('datetime')
    
    if not classname or not datetime_str:
        return jsonify({'error': 'Missing classname or datetime parameter'}), 400
    
    log_dir = get_log_directory()
    log_file_path = log_dir / classname / f"{classname}_{datetime_str}.log"
    
    if not log_file_path.exists():
        return jsonify({'error': 'Log file not found'}), 404
    
    try:
        with open(log_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({'content': content})
    except Exception as e:
        return jsonify({'error': f'Error reading log file: {str(e)}'}), 500