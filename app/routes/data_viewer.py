from flask import Blueprint, render_template, jsonify, request

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

@viewer_bp.route('/api/delete_all_cycle')
def delete_all_cycle():
    success = get_app_state().database.delete_all_cycles()
    if success:
        result = {"status": "success", "message": "Action performed"}
        return jsonify(result), 200  # HTTP 200 OK
    else:
        result = {"status": "error", "message": "Deleting cycles failed"}
        return jsonify(result), 500  # Internal Server Error
    

@viewer_bp.route('/api/data/<cycle_name>')
def get_cycle_data(cycle_name):
    readings = get_app_state().database.read_cycle_data(cycle_name)
    test = jsonify(readings)
    return jsonify(readings)

@viewer_bp.route('/api/import_cycle', methods=['POST'])
def import_cycle():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"status": "error", "message": "No data received"}), 400
        
        cycle_name = data.get('cycle_name')
        sensor_data = data.get('sensor_data', {})
        calculation_data = data.get('calculation_data', [])
        
        if not cycle_name:
            return jsonify({"status": "error", "message": "Cycle name is required"}), 400
        
        # Check if cycle already exists
        existing_cycles = get_app_state().database.list_cycle_names()
        if cycle_name in existing_cycles:
            return jsonify({"status": "error", "message": f"Cycle '{cycle_name}' already exists"}), 409
        
        # Import data by directly inserting into database tables
        database = get_app_state().database
        
        # First, create the cycle
        with database.get_connection() as conn:
            cursor = conn.cursor()
            
            # Insert the cycle
            cursor.execute(
                "INSERT INTO cycles (name, start_time, end_time) VALUES (?, ?, ?)",
                (cycle_name, "imported", "imported")
            )
            cycle_id = cursor.lastrowid
            
            # Insert sensor data
            for sensor_type, sensor_arrays in sensor_data.items():
                if isinstance(sensor_arrays, list) and len(sensor_arrays) > 0:
                    for sensor_array in sensor_arrays:
                        if isinstance(sensor_array, list):
                            for sensor_reading in sensor_array:
                                if len(sensor_reading) >= 3:
                                    sensor_id, timestamp, value = sensor_reading[:3]
                                    
                                    # Skip None values (failed sensor readings)
                                    if value is None:
                                        continue
                                    
                                    # Convert value to float, skip if conversion fails
                                    try:
                                        float_value = float(value)
                                    except (ValueError, TypeError):
                                        continue
                                        
                                    cursor.execute(
                                        "INSERT INTO sensor_readings (sensor_type, cycle_id, sensor_id, timestamp, value) VALUES (?, ?, ?, ?, ?)",
                                        (sensor_type, cycle_id, sensor_id, timestamp, float_value)
                                    )
            
            # Insert calculation data
            for calc_data in calculation_data:
                # Handle both old format (6 fields) and new format (7 fields with control_status)
                if len(calc_data) >= 6:
                    calculation_name, timestamp, pid_output, current_temp, target_temp, error = calc_data[:6]
                    control_status = calc_data[6] if len(calc_data) > 6 else "UNKNOWN"
                    
                    # Convert values to float, skip record if any critical values are None or invalid
                    try:
                        float_pid_output = float(pid_output) if pid_output is not None else 0.0
                        float_current_temp = float(current_temp) if current_temp is not None else 0.0
                        float_target_temp = float(target_temp) if target_temp is not None else 0.0
                        float_error = float(error) if error is not None else 0.0
                    except (ValueError, TypeError):
                        continue
                        
                    cursor.execute(
                        "INSERT INTO calculation_data (cycle_id, calculation_name, timestamp, pid_output, current_temp, target_temp, error, control_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (cycle_id, calculation_name, timestamp, float_pid_output, float_current_temp, float_target_temp, float_error, control_status)
                    )
            
            conn.commit()
        
        return jsonify({
            "status": "success", 
            "message": f"Cycle '{cycle_name}' imported successfully"
        }), 200
        
    except Exception as e:
        return jsonify({
            "status": "error", 
            "message": f"Import failed: {str(e)}"
        }), 500