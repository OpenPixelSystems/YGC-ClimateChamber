/**
 * Database Viewer - Using Universal Chart Manager
 */

import UniversalChartManager from './universal-chart-manager.js';

class DatabaseViewer {
    constructor() {
        this.chartManager = new UniversalChartManager({
            canvasId: 'temperatureChart',
            type: 'database'
        });
        
        this.dropdown = document.getElementById('cycleDropdown');
        this.displayTypeDropdown = document.getElementById('displayType');
        
        this.initChart();
        this.bindEvents();
        this.loadCycles();
    }

    initChart() {
        this.chartManager.init();
    }

    bindEvents() {
        // Dropdown changes
        this.dropdown.addEventListener('change', () => {
            const cycleId = this.dropdown.value;
            this.loadCycleData(cycleId);
        });

        this.displayTypeDropdown.addEventListener('change', () => {
            const cycleId = this.dropdown.value;
            this.loadCycleData(cycleId);
        });

        // Action buttons
        document.getElementById('deleteData').addEventListener('click', () => this.deleteCycle());
        document.getElementById('deleteAllData').addEventListener('click', () => this.deleteAllCycles());
        document.getElementById('exportData').addEventListener('click', () => this.exportData());
    }

    async loadCycles() {
        try {
            const res = await fetch('/api/cycles');
            if (!res.ok) throw new Error('Failed to fetch cycles');
            const data = await res.json();

            this.dropdown.innerHTML = '';
            data.forEach(cycle => {
                const option = document.createElement('option');
                option.textContent = cycle;
                option.value = cycle;
                this.dropdown.appendChild(option);
            });

            if (data.length > 0) {
                this.loadCycleData(data[0]);
            }
        } catch (error) {
            console.error('Error loading cycles:', error);
        }
    }

    async loadCycleData(cycle_name) {
        try {
            const res = await fetch(`/api/data/${cycle_name}`);
            if (!res.ok) throw new Error('Failed to fetch cycle data');
            const data = await res.json();

            const displayType = this.displayTypeDropdown.value;
            const datasets = this.processDataForDisplay(data, displayType);
            
            this.updateChartTitle(displayType);
            this.chartManager.loadDatabaseData(datasets);
        } catch (error) {
            console.error('Error loading cycle data:', error);
        }
    }

    processDataForDisplay(data, displayType) {
        const sensors = {};
        const calculations = {};

        // Process sensor data
        if (data.sensor_data && typeof data.sensor_data === 'object') {
            Object.entries(data.sensor_data).forEach(([sensorType, sensorArrays]) => {
                if (Array.isArray(sensorArrays)) {
                    sensorArrays.forEach(sensorArray => {
                        if (Array.isArray(sensorArray)) {
                            sensorArray.forEach(([sensor_id, timestamp, value]) => {
                                // Filter based on display type
                                if (displayType !== 'all') {
                                    const sensorTypeLower = sensorType.toLowerCase();
                                    if (displayType === 'temperature' && sensorTypeLower !== 'temperature') return;
                                    if (displayType === 'humidity' && sensorTypeLower !== 'humidity') return;
                                    if (displayType === 'current' && sensorTypeLower !== 'current') return;
                                    if (displayType === 'calculations') return;
                                }

                                if (!sensors[sensor_id]) {
                                    sensors[sensor_id] = { timestamps: [], values: [] };
                                }

                                sensors[sensor_id].timestamps.push(timestamp);
                                sensors[sensor_id].values.push(value);
                            });
                        }
                    });
                }
            });
        }

        // Process calculation data
        if (data.calculation_data && Array.isArray(data.calculation_data)) {
            data.calculation_data.forEach(([calculation_name, timestamp, pid_output, current_temp, target_temp, error]) => {
                if (displayType !== 'all' && displayType !== 'calculations') return;

                const metrics = {
                    [`${calculation_name}_PID_Output`]: pid_output,
                    [`${calculation_name}_Current_Temp`]: current_temp,
                    [`${calculation_name}_Target_Temp`]: target_temp,
                    [`${calculation_name}_Error`]: error
                };

                Object.entries(metrics).forEach(([metricName, value]) => {
                    if (!calculations[metricName]) {
                        calculations[metricName] = { timestamps: [], values: [] };
                    }
                    calculations[metricName].timestamps.push(timestamp);
                    calculations[metricName].values.push(value);
                });
            });
        }

        // Create datasets
        const sensorDatasets = Object.entries(sensors).map(([sensor, data]) => ({
            label: sensor,
            data: data.timestamps.map((timestamp, i) => ({
                x: new Date(timestamp),
                y: data.values[i]
            })),
            borderColor: this.getRandomColor(),
            backgroundColor: this.getRandomColor(0.1),
            fill: false,
            tension: 0.3,
            pointRadius: 3,
            yAxisID: 'y'
        }));

        const calculationDatasets = Object.entries(calculations).map(([calcName, data]) => {
            const isError = calcName.includes('Error');
            const isPIDOutput = calcName.includes('PID_Output');

            return {
                label: calcName,
                data: data.timestamps.map((timestamp, i) => ({
                    x: new Date(timestamp),
                    y: data.values[i]
                })),
                borderColor: this.getRandomColor(),
                backgroundColor: this.getRandomColor(0.1),
                fill: false,
                tension: 0.3,
                pointRadius: 2,
                borderDash: isPIDOutput ? [5, 5] : [],
                yAxisID: isError ? 'y1' : 'y'
            };
        });

        return [...sensorDatasets, ...calculationDatasets];
    }

    updateChartTitle(displayType) {
        const chart = this.chartManager.getChart();
        if (!chart) return;

        const title = `Sensor ${displayType === 'all' ? 'Data' : displayType.charAt(0).toUpperCase() + displayType.slice(1)} Over Time`;
        
        if (!chart.options.plugins.title) {
            chart.options.plugins.title = {};
        }
        
        chart.options.plugins.title.display = true;
        chart.options.plugins.title.text = title;

        // Update Y axis label
        const yAxisLabel = displayType === 'humidity' ? 'Humidity (%)' : 'Temperature (°C)';
        if (chart.options.scales.y && chart.options.scales.y.title) {
            chart.options.scales.y.title.text = yAxisLabel;
        }
    }

    async deleteCycle() {
        try {
            const cycleName = this.dropdown.value;
            const res = await fetch(`/api/delete_cycle/${cycleName}`);
            const data = await res.json();

            if (!res.ok) {
                throw new Error(data.message || 'Failed to delete cycle');
            }

            // Remove option from dropdown
            const optionToRemove = Array.from(this.dropdown.options).find(opt => opt.value === cycleName);
            if (optionToRemove) {
                optionToRemove.remove();
            }

            // Reset dropdown or show placeholder
            if (this.dropdown.options.length > 0) {
                this.dropdown.selectedIndex = 0;
                this.loadCycleData(this.dropdown.value);
            } else {
                this.chartManager.clearData();
            }

            alert(`Cycle ${cycleName} deleted successfully.`);
        } catch (error) {
            alert(error.message);
        }
    }

    async deleteAllCycles() {
        try {
            const res = await fetch(`/api/delete_all_cycle`);
            const data = await res.json();

            if (!res.ok) {
                throw new Error(data.message || 'Failed to delete all cycles');
            }

            alert(`✅ Success: ${data.message || 'Cycles deleted successfully'}`);
            this.loadCycles(); // Reload cycles list
        } catch (err) {
            alert(`❌ Error: ${err.message}`);
        }
    }

    async exportData() {
        try {
            const cycleId = this.dropdown.value;
            if (!cycleId) {
                alert('Please select a cycle to export.');
                return;
            }

            // Show format selection dialog
            const format = await this.showFormatSelectionDialog();
            if (!format) return; // User cancelled

            const res = await fetch(`/api/data/${cycleId}`);
            if (!res.ok) throw new Error('Failed to fetch data for export');
            const rawData = await res.json();

            // Process data for export
            const exportData = this.prepareExportData(rawData);
            
            // Generate file content based on selected format
            let fileContent, fileName, mimeType;
            
            switch (format) {
                case 'csv':
                    fileContent = this.generateCSV(exportData);
                    fileName = `${cycleId}_cycle_data.csv`;
                    mimeType = 'text/csv';
                    break;
                case 'json':
                    fileContent = this.generateJSON(exportData, cycleId);
                    fileName = `${cycleId}_cycle_data.json`;
                    mimeType = 'application/json';
                    break;
                case 'txt':
                    fileContent = this.generateTXT(exportData, cycleId);
                    fileName = `${cycleId}_cycle_data.txt`;
                    mimeType = 'text/plain';
                    break;
                case 'excel':
                    fileContent = this.generateExcel(exportData);
                    fileName = `${cycleId}_cycle_data.xlsx`;
                    mimeType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
                    break;
            }

            // Download the file
            this.downloadFile(fileContent, fileName, mimeType);
            
        } catch (error) {
            console.error('Error exporting data:', error);
            alert('Failed to export data. Please try again.');
        }
    }

    async showFormatSelectionDialog() {
        return new Promise((resolve) => {
            const modal = document.createElement('div');
            modal.style.cssText = `
                position: fixed; top: 0; left: 0; width: 100%; height: 100%;
                background: rgba(0,0,0,0.5); display: flex; justify-content: center;
                align-items: center; z-index: 1000;
            `;
            
            const dialog = document.createElement('div');
            dialog.style.cssText = `
                background: var(--card-background); 
                color: var(--text-color);
                padding: 20px; 
                border-radius: 8px;
                box-shadow: 0 4px 8px var(--shadow-color); 
                max-width: 400px; 
                width: 90%;
                border: 1px solid var(--border-color);
            `;
            
            dialog.innerHTML = `
                <h3 style="margin-top: 0; color: var(--text-color);">Export Format</h3>
                <p style="color: var(--text-color);">Choose the format for exporting cycle data:</p>
                <div style="margin: 15px 0;">
                    <label style="display: block; margin: 8px 0; cursor: pointer; color: var(--text-color);">
                        <input type="radio" name="exportFormat" value="csv" checked style="margin-right: 8px;">
                        CSV (Comma Separated Values) - Excel compatible
                    </label>
                    <label style="display: block; margin: 8px 0; cursor: pointer; color: var(--text-color);">
                        <input type="radio" name="exportFormat" value="json" style="margin-right: 8px;">
                        JSON (JavaScript Object Notation) - Developer friendly
                    </label>
                    <label style="display: block; margin: 8px 0; cursor: pointer; color: var(--text-color);">
                        <input type="radio" name="exportFormat" value="txt" style="margin-right: 8px;">
                        TXT (Plain Text) - Human readable
                    </label>
                    <label style="display: block; margin: 8px 0; cursor: pointer; color: var(--text-color);">
                        <input type="radio" name="exportFormat" value="excel" style="margin-right: 8px;">
                        Excel (XLSX) - Microsoft Excel format
                    </label>
                </div>
                <div style="text-align: right; margin-top: 20px;">
                    <button id="exportCancel" style="
                        margin-right: 10px; 
                        padding: 8px 16px; 
                        border: 1px solid var(--border-color); 
                        background: var(--card-background); 
                        color: var(--text-color);
                        border-radius: 4px; 
                        cursor: pointer;
                        transition: background-color 0.2s;
                    ">Cancel</button>
                    <button id="exportConfirm" style="
                        padding: 8px 16px; 
                        background: var(--success-color); 
                        color: white; 
                        border: none; 
                        border-radius: 4px; 
                        cursor: pointer;
                        transition: background-color 0.2s;
                    ">Export</button>
                </div>
            `;
            
            modal.appendChild(dialog);
            document.body.appendChild(modal);
            
            // Add hover effects for buttons
            const cancelButton = document.getElementById('exportCancel');
            const confirmButton = document.getElementById('exportConfirm');
            
            cancelButton.addEventListener('mouseenter', () => {
                cancelButton.style.background = 'var(--nav-hover)';
            });
            cancelButton.addEventListener('mouseleave', () => {
                cancelButton.style.background = 'var(--card-background)';
            });
            
            confirmButton.addEventListener('mouseenter', () => {
                confirmButton.style.background = '#27ae60'; // Darker green
            });
            confirmButton.addEventListener('mouseleave', () => {
                confirmButton.style.background = 'var(--success-color)';
            });
            
            cancelButton.onclick = () => {
                document.body.removeChild(modal);
                resolve(null);
            };
            
            confirmButton.onclick = () => {
                const selected = dialog.querySelector('input[name="exportFormat"]:checked');
                document.body.removeChild(modal);
                resolve(selected ? selected.value : null);
            };
            
            // Close on background click
            modal.onclick = (e) => {
                if (e.target === modal) {
                    document.body.removeChild(modal);
                    resolve(null);
                }
            };
        });
    }

    prepareExportData(rawData) {
        const exportData = {
            sensorData: [],
            calculationData: []
        };

        // Process sensor data
        if (rawData.sensor_data && typeof rawData.sensor_data === 'object') {
            Object.entries(rawData.sensor_data).forEach(([sensorType, sensorArrays]) => {
                if (Array.isArray(sensorArrays)) {
                    sensorArrays.forEach(sensorArray => {
                        if (Array.isArray(sensorArray)) {
                            sensorArray.forEach(([sensor_id, timestamp, value]) => {
                                exportData.sensorData.push({
                                    sensorType,
                                    sensorId: sensor_id,
                                    timestamp: new Date(timestamp).toISOString(),
                                    value: value,
                                    unit: this.getSensorUnit(sensorType)
                                });
                            });
                        }
                    });
                }
            });
        }

        // Process calculation data
        if (rawData.calculation_data && Array.isArray(rawData.calculation_data)) {
            rawData.calculation_data.forEach(([calculation_name, timestamp, pid_output, current_temp, target_temp, error]) => {
                exportData.calculationData.push({
                    calculationName: calculation_name,
                    timestamp: new Date(timestamp).toISOString(),
                    pidOutput: pid_output,
                    currentTemp: current_temp,
                    targetTemp: target_temp,
                    error: error
                });
            });
        }

        return exportData;
    }

    getSensorUnit(sensorType) {
        const lowerType = sensorType.toLowerCase();
        if (lowerType.includes('temp')) return '°C';
        if (lowerType.includes('current')) return 'A';
        if (lowerType.includes('pressure')) return 'Pa';
        if (lowerType.includes('humidity')) return '%';
        if (lowerType.includes('voltage')) return 'V';
        return '';
    }

    generateCSV(data) {
        let csv = '';
        
        // Sensor data section
        if (data.sensorData.length > 0) {
            csv += 'SENSOR DATA\n';
            csv += 'Sensor Type,Sensor ID,Timestamp,Value,Unit\n';
            data.sensorData.forEach(row => {
                csv += `"${row.sensorType}","${row.sensorId}","${row.timestamp}",${row.value},"${row.unit}"\n`;
            });
            csv += '\n';
        }

        // Calculation data section
        if (data.calculationData.length > 0) {
            csv += 'CALCULATION DATA\n';
            csv += 'Calculation Name,Timestamp,PID Output,Current Temperature,Target Temperature,Error\n';
            data.calculationData.forEach(row => {
                csv += `"${row.calculationName}","${row.timestamp}",${row.pidOutput},${row.currentTemp},${row.targetTemp},${row.error}\n`;
            });
        }

        return csv;
    }

    generateJSON(data, cycleId) {
        const exportObject = {
            metadata: {
                cycleName: cycleId,
                exportDate: new Date().toISOString(),
                totalSensorReadings: data.sensorData.length,
                totalCalculationEntries: data.calculationData.length
            },
            sensorData: data.sensorData,
            calculationData: data.calculationData
        };
        
        return JSON.stringify(exportObject, null, 2);
    }

    generateTXT(data, cycleId) {
        let txt = `Climate Chamber Cycle Data Export\n`;
        txt += `================================\n\n`;
        txt += `Cycle Name: ${cycleId}\n`;
        txt += `Export Date: ${new Date().toLocaleString()}\n`;
        txt += `Total Sensor Readings: ${data.sensorData.length}\n`;
        txt += `Total Calculation Entries: ${data.calculationData.length}\n\n`;

        if (data.sensorData.length > 0) {
            txt += `SENSOR DATA\n`;
            txt += `-----------\n`;
            data.sensorData.forEach(row => {
                txt += `${row.timestamp} | ${row.sensorType} | ${row.sensorId} | ${row.value} ${row.unit}\n`;
            });
            txt += `\n`;
        }

        if (data.calculationData.length > 0) {
            txt += `CALCULATION DATA\n`;
            txt += `----------------\n`;
            data.calculationData.forEach(row => {
                txt += `${row.timestamp} | ${row.calculationName} | PID: ${row.pidOutput} | Current: ${row.currentTemp}°C | Target: ${row.targetTemp}°C | Error: ${row.error}\n`;
            });
        }

        return txt;
    }

    generateExcel(data) {
        // For Excel format, we'll generate a simple tab-separated values format
        // that Excel can open directly
        let excel = '';
        
        // Sensor data worksheet
        if (data.sensorData.length > 0) {
            excel += 'SENSOR DATA\t\t\t\t\n';
            excel += 'Sensor Type\tSensor ID\tTimestamp\tValue\tUnit\n';
            data.sensorData.forEach(row => {
                excel += `${row.sensorType}\t${row.sensorId}\t${row.timestamp}\t${row.value}\t${row.unit}\n`;
            });
            excel += '\n\n';
        }

        // Calculation data worksheet
        if (data.calculationData.length > 0) {
            excel += 'CALCULATION DATA\t\t\t\t\t\n';
            excel += 'Calculation Name\tTimestamp\tPID Output\tCurrent Temperature\tTarget Temperature\tError\n';
            data.calculationData.forEach(row => {
                excel += `${row.calculationName}\t${row.timestamp}\t${row.pidOutput}\t${row.currentTemp}\t${row.targetTemp}\t${row.error}\n`;
            });
        }

        return excel;
    }

    downloadFile(content, fileName, mimeType) {
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        
        const link = document.createElement('a');
        link.href = url;
        link.download = fileName;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        // Clean up the URL object
        URL.revokeObjectURL(url);
        
        // Show success message
        alert(`✅ Export successful! File "${fileName}" has been downloaded.`);
    }

    getRandomColor(alpha = 1) {
        const r = Math.floor(Math.random() * 120) + 80;
        const g = Math.floor(Math.random() * 120) + 80;
        const b = Math.floor(Math.random() * 120) + 80;
        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    }
}

// Initialize when page loads
window.onload = () => {
    new DatabaseViewer();
};