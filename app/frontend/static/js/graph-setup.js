/**
 * Graph Setup - Temperature Profile Editor
 * Using Universal Chart Manager
 */

import UniversalChartManager from './universal-chart-manager.js';

class GraphSetup {
    constructor() {
        this.chartManager = new UniversalChartManager({
            canvasId: 'myChart',
            type: 'setup'
        });

        this.unsavedChanges = false;
        this.startingTemperature = null;
        
        // Set reference start time to current time
        this.chartManager.setReferenceStartTime(new Date());
        
        this.initChart();
        this.bindEvents();
        this.updateUndoButton();
        
        // Load starting temperature on page load
        this.fetchStartingTemperature();
    }

    initChart() {
        this.chartManager.init();
        
        // Set up callback for when points are added via chart clicks
        this.chartManager.onPointAddedCallback = () => {
            this.unsavedChanges = this.chartManager.unsavedChanges;
            this.updateUndoButton();
        };
    }

    bindEvents() {
        // Form submission
        document.getElementById('pointForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.addPointFromInput();
        });

        // Buttons
        document.getElementById('undoButton').addEventListener('click', () => this.undoLastPoint());
        document.getElementById('clearPoints').addEventListener('click', () => this.clearAllPoints());
        document.getElementById('sendPointsToServer').addEventListener('click', () => this.saveToServer());
        document.getElementById('refreshStartingTemp').addEventListener('click', () => this.fetchStartingTemperature());
        
        // Interpolation change
        document.getElementById('interpolationMethod').addEventListener('change', () => this.updateInterpolation());

        // Warn about unsaved changes
        window.addEventListener('beforeunload', (event) => {
            if (this.unsavedChanges) {
                event.returnValue = "You have unsaved changes. Are you sure you want to leave?";
                return event.returnValue;
            }
        });
    }

    addPointFromInput() {
        const temperature = parseFloat(document.getElementById('temperatureInput').value);
        const timeOffsetStr = document.getElementById('timeOffsetInput').value.trim();
        
        if (isNaN(temperature)) {
            alert('Please enter a valid temperature value');
            return;
        }
        
        if (!timeOffsetStr) {
            alert('Please enter a time offset (e.g., 2h, 30m, 90s)');
            return;
        }
        
        if (this.startingTemperature === null) {
            alert('Starting temperature not available. Please wait for sensors to load.');
            return;
        }
        
        // Parse time offset to seconds
        const timeOffsetSeconds = this.parseTimeOffset(timeOffsetStr);
        if (timeOffsetSeconds === null) {
            alert('Invalid time format. Use format like: 2h, 30m, 90s, or combinations like 1h30m');
            return;
        }
        
        // Find the last (highest) time point to add offset to
        let targetTime = timeOffsetSeconds; // Default to offset from start (0)
        
        if (this.chartManager.points.length > 0) {
            // Sort points by time to find the latest one
            const sortedPoints = [...this.chartManager.points].sort((a, b) => a.x - b.x);
            const lastPoint = sortedPoints[sortedPoints.length - 1];
            targetTime = lastPoint.x + timeOffsetSeconds; // Add offset to last point's time
        }
        
        // Add point at cumulative time
        this.chartManager.addPoint(targetTime, temperature);
        this.unsavedChanges = this.chartManager.unsavedChanges;
        this.updateUndoButton();
        
        // Clear inputs
        document.getElementById('temperatureInput').value = '';
        document.getElementById('timeOffsetInput').value = '';
    }

    undoLastPoint() {
        if (this.chartManager.points.length === 0) {
            alert('No points to undo');
            return;
        }

        this.chartManager.points.pop();
        this.chartManager.updateSetupChart();
        this.updateUndoButton();
        
        if (this.chartManager.points.length === 0) {
            this.unsavedChanges = false;
            this.chartManager.unsavedChanges = false;
            // Refresh starting point when all points are cleared
            this.fetchStartingTemperature();
        } else {
            this.unsavedChanges = true;
            this.chartManager.unsavedChanges = true;
        }
    }

    clearAllPoints() {
        if (this.chartManager.points.length === 0) return;
        
        if (confirm('Are you sure you want to clear all points?')) {
            this.chartManager.clearData();
            this.unsavedChanges = false;
            this.updateUndoButton();
            // Refresh starting point when all points are cleared
            this.fetchStartingTemperature();
        }
    }

    updateInterpolation() {
        const method = document.getElementById('interpolationMethod').value;
        const chart = this.chartManager.getChart();
        if (!chart) return;
        
        const dataset = chart.data.datasets[0];
        if (!dataset) return;
        
        if (method === 'linear') {
            dataset.tension = 0;
            dataset.cubicInterpolationMode = 'default';
        } else {
            dataset.tension = 0.4;
            dataset.cubicInterpolationMode = 'monotone';
        }
        
        chart.update();
    }

    updateUndoButton() {
        const button = document.getElementById('undoButton');
        const pointCount = this.chartManager.points.length;
        button.disabled = pointCount === 0;
        button.textContent = pointCount === 0 ? 'Undo Last' : `Undo Last (${pointCount})`;
    }

    async fetchStartingTemperature() {
        try {
            const response = await fetch('/get_starting_temperature');
            const data = await response.json();
            
            const valueElement = document.getElementById('startingTempValue');
            
            if (data.success && data.starting_temperature !== null) {
                this.startingTemperature = data.starting_temperature;
                valueElement.textContent = data.starting_temperature.toFixed(1);
                valueElement.style.color = '#4CAF50'; // Green for success
                
                // Add/update starting temperature as first setpoint
                this.updateFirstSetpoint(this.startingTemperature);
            } else {
                this.startingTemperature = null;
                valueElement.textContent = 'N/A';
                valueElement.style.color = '#f44336'; // Red for error
                console.warn('Starting temperature unavailable:', data.message);
            }
        } catch (error) {
            this.startingTemperature = null;
            document.getElementById('startingTempValue').textContent = 'Error';
            document.getElementById('startingTempValue').style.color = '#f44336';
            console.error('Error fetching starting temperature:', error);
        }
    }

    updateFirstSetpoint(temperature) {
        // Check if there are existing points
        if (this.chartManager.points.length > 0) {
            // Sort points by offset to find the earliest
            const sortedPoints = [...this.chartManager.points].sort((a, b) => a.x - b.x);
            const firstPoint = sortedPoints[0];
            
            // If the first point is at time 0 (or within 5 minutes), replace it
            if (firstPoint.x <= 300) { // 5 minutes in seconds
                const index = this.chartManager.points.findIndex(p => p === firstPoint);
                this.chartManager.points[index] = {x: 0, y: temperature};
            } else {
                // Insert new starting point at time 0
                this.chartManager.points.unshift({x: 0, y: temperature});
            }
        } else {
            // Add the starting point as the first point at time 0
            this.chartManager.addPoint(0, temperature);
        }
        
        // Update the chart to show the new starting point
        this.chartManager.updateSetupChart();
        this.chartManager.updateDynamicScaling();
        this.updateUndoButton();
    }

    parseTimeOffset(timeStr) {
        // Parse time formats like: 2h, 30m, 90s, 1h30m, 2h15m30s
        const timeStr_lower = timeStr.toLowerCase().trim();
        let totalSeconds = 0;
        
        // Extract hours
        const hoursMatch = timeStr_lower.match(/(\d+(?:\.\d+)?)h/);
        if (hoursMatch) {
            totalSeconds += parseFloat(hoursMatch[1]) * 3600;
        }
        
        // Extract minutes
        const minutesMatch = timeStr_lower.match(/(\d+(?:\.\d+)?)m/);
        if (minutesMatch) {
            totalSeconds += parseFloat(minutesMatch[1]) * 60;
        }
        
        // Extract seconds
        const secondsMatch = timeStr_lower.match(/(\d+(?:\.\d+)?)s/);
        if (secondsMatch) {
            totalSeconds += parseFloat(secondsMatch[1]);
        }
        
        // If no valid time units found, return null
        if (totalSeconds === 0 && !hoursMatch && !minutesMatch && !secondsMatch) {
            return null;
        }
        
        return totalSeconds;
    }

    async saveToServer() {
        if (this.chartManager.points.length === 0) {
            alert('No points to save');
            return;
        }

        try {
            // Points are already stored as offset seconds, just sort them
            const sortedPoints = [...this.chartManager.points].sort((a, b) => a.x - b.x);

            const response = await fetch('/store-graph-data', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify([{
                    label: 'Temperature Profile',
                    data: sortedPoints
                }])
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to save');
            }

            this.unsavedChanges = false;

            if (confirm('Graph saved successfully! Would you like to view it?')) {
                window.location.href = '/display-graph';
            }
        } catch (error) {
            alert(`Error saving graph: ${error.message}`);
        }
    }

}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    new GraphSetup();
});