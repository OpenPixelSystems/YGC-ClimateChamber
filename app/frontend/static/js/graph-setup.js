/**
 * Graph Setup - Temperature Profile Editor
 * Simplified and cleaned up version
 */

class GraphSetup {
    constructor() {
        this.points = [];
        this.unsavedChanges = false;
        this.initChart();
        this.bindEvents();
        this.updateUndoButton();
    }

    initChart() {
        const ctx = document.getElementById('myChart').getContext('2d');
        this.chart = new Chart(ctx, {
            type: 'line',
            data: {
                datasets: [{
                    label: 'Temperature Profile',
                    data: [],
                    borderColor: 'rgba(75, 192, 192, 1)',
                    backgroundColor: 'rgba(75, 192, 192, 0.1)',
                    borderWidth: 2,
                    fill: false,
                    tension: 0,
                    pointRadius: 6,
                    pointHoverRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 0 },
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                scales: {
                    x: {
                        type: 'linear',
                        position: 'bottom',
                        min: 0,
                        max: 120,
                        title: { 
                            display: true, 
                            text: 'Time (minutes)',
                            font: { size: 14 }
                        },
                        grid: { color: 'rgba(0,0,0,0.1)' }
                    },
                    y: {
                        min: -20,
                        max: 180,
                        title: { 
                            display: true, 
                            text: 'Temperature (°C)',
                            font: { size: 14 }
                        },
                        grid: { color: 'rgba(0,0,0,0.1)' }
                    }
                },
                onClick: (event) => this.handleChartClick(event),
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    }
                }
            }
        });
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

    handleChartClick(event) {
        const canvasPosition = Chart.helpers.getRelativePosition(event, this.chart);
        const x = this.chart.scales.x.getValueForPixel(canvasPosition.x);
        const y = this.chart.scales.y.getValueForPixel(canvasPosition.y);

        // Round to reasonable increments
        const roundedX = Math.round(x / 5) * 5;
        const roundedY = Math.round(y);

        this.addPoint(roundedX, roundedY);
    }

    addPointFromInput() {
        const input = document.getElementById('pointInput').value.trim();
        if (!input) return;

        const [x, y] = input.split(',').map(Number);
        if (isNaN(x) || isNaN(y)) {
            alert('Please enter valid numbers in format: time,temperature');
            return;
        }

        this.addPoint(x, y);
        document.getElementById('pointInput').value = '';
    }

    addPoint(x, y) {
        // Validate ranges
        if (x < 0 || x > 120) {
            alert('Time must be between 0 and 120 minutes');
            return;
        }
        if (y < -20 || y > 180) {
            alert('Temperature must be between -20 and 180°C');
            return;
        }

        // Check for duplicate time points
        const existingIndex = this.points.findIndex(point => point.x === x);
        if (existingIndex !== -1) {
            // Update existing point
            this.points[existingIndex].y = y;
        } else {
            // Add new point
            this.points.push({ x, y });
        }

        this.updateChart();
        this.markUnsaved();
    }

    undoLastPoint() {
        if (this.points.length === 0) {
            alert('No points to undo');
            return;
        }

        this.points.pop();
        this.updateChart();
        
        if (this.points.length === 0) {
            this.unsavedChanges = false;
        }
    }

    clearAllPoints() {
        if (this.points.length === 0) return;
        
        if (confirm('Are you sure you want to clear all points?')) {
            this.points = [];
            this.updateChart();
            this.unsavedChanges = false;
        }
    }

    updateChart() {
        // Sort points by time
        this.points.sort((a, b) => a.x - b.x);
        
        // Update chart data
        this.chart.data.datasets[0].data = [...this.points];
        this.chart.update('none'); // No animation for better performance
        
        this.updateUndoButton();
    }

    updateInterpolation() {
        const method = document.getElementById('interpolationMethod').value;
        const dataset = this.chart.data.datasets[0];
        
        if (method === 'linear') {
            dataset.tension = 0;
            dataset.cubicInterpolationMode = 'default';
        } else {
            dataset.tension = 0.4;
            dataset.cubicInterpolationMode = 'monotone';
        }
        
        this.chart.update();
    }

    updateUndoButton() {
        const button = document.getElementById('undoButton');
        button.disabled = this.points.length === 0;
        button.textContent = this.points.length === 0 ? 'Undo Last' : `Undo Last (${this.points.length})`;
    }

    markUnsaved() {
        this.unsavedChanges = true;
        this.updateStatusIndicator();
    }

    updateStatusIndicator() {
        const indicator = document.getElementById('connectionStatusCircle');
        if (this.unsavedChanges) {
            indicator.style.backgroundColor = 'orange';
            indicator.title = 'Unsaved changes';
        } else {
            indicator.style.backgroundColor = 'green';
            indicator.title = 'All changes saved';
        }
    }

    async saveToServer() {
        if (this.points.length === 0) {
            alert('No points to save');
            return;
        }

        try {
            const response = await fetch('/store-graph-data', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify([{
                    label: 'Temperature Profile',
                    data: this.points
                }])
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to save');
            }

            this.unsavedChanges = false;
            this.updateStatusIndicator();
            
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