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
            const res = await fetch(`/api/data/${cycleId}`);
            if (!res.ok) throw new Error('Failed to fetch data for export');
            const data = await res.json();

            // Convert data to CSV
            const csvContent = 'data:text/csv;charset=utf-8,' +
                'Sensor,Timestamp,Value\n' +
                data.map(row => row.join(',')).join('\n');

            // Create download link
            const encodedUri = encodeURI(csvContent);
            const link = document.createElement('a');
            link.setAttribute('href', encodedUri);
            link.setAttribute('download', `${cycleId}_sensor_data.csv`);
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        } catch (error) {
            console.error('Error exporting data:', error);
            alert('Failed to export data. Please try again.');
        }
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