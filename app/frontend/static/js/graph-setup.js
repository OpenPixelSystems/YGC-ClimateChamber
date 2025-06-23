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
        this.initChart();
        this.bindEvents();
        this.updateUndoButton();
    }

    initChart() {
        this.chartManager.init();
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
        const input = document.getElementById('pointInput').value.trim();
        if (!input) return;

        const [x, y] = input.split(',').map(Number);
        if (isNaN(x) || isNaN(y)) {
            alert('Please enter valid numbers in format: time,temperature');
            return;
        }

        this.chartManager.addPoint(x, y);
        this.unsavedChanges = this.chartManager.unsavedChanges;
        this.updateUndoButton();
        document.getElementById('pointInput').value = '';
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
        }
    }

    clearAllPoints() {
        if (this.chartManager.points.length === 0) return;
        
        if (confirm('Are you sure you want to clear all points?')) {
            this.chartManager.clearData();
            this.unsavedChanges = false;
            this.updateUndoButton();
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

    async saveToServer() {
        if (this.chartManager.points.length === 0) {
            alert('No points to save');
            return;
        }

        try {
            const response = await fetch('/store-graph-data', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify([{
                    label: 'Temperature Profile',
                    data: this.chartManager.points
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