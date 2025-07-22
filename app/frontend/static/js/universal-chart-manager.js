/**
 * Universal Chart Manager
 * Handles all chart operations across different pages
 */

import { formatTime, getRandomColor } from './utils.js';

export default class UniversalChartManager {
    constructor(config = {}) {
        this.chartInstance = null;
        this.config = {
            canvasId: config.canvasId || 'chart',
            type: config.type || 'realtime', // 'realtime', 'static', 'database', 'setup'
            responsive: config.responsive !== false,
            maintainAspectRatio: config.maintainAspectRatio || false,
            animation: config.animation || false,
            ...config
        };
        
        // Real-time specific properties
        this.startTime = null;
        this.maxElapsedSeconds = 0;
        this.startTimeLineConfig = null;
        
        // Static/setup specific properties
        this.points = [];
        this.unsavedChanges = false;
        this.onPointAddedCallback = null;

        // Zoom functionality properties
        this.isDragging = false;
        this.dragStart = null;
        this.dragEnd = null;
        this.selectionOverlay = null;
        this.originalXLimits = null;
    }

    /**
     * Initialize the chart with type-specific configuration
     */
    init() {
        const canvas = document.getElementById(this.config.canvasId);
        if (!canvas) {
            console.error(`Canvas with id '${this.config.canvasId}' not found`);
            return;
        }

        const ctx = canvas.getContext('2d');
        const chartConfig = this.createChartConfig();
        
        if (this.chartInstance) {
            this.chartInstance.destroy();
        }
        
        this.chartInstance = new Chart(ctx, chartConfig);
        
        // Type-specific initialization
        if (this.config.type === 'setup') {
            this.setupInteractiveChart();
        }
        
        // Add zoom functionality for database charts
        if (this.config.type === 'database') {
            this.setupZoomFunctionality();
        }

        return this.chartInstance;
    }

    /**
     * Create chart configuration based on type
     */
    createChartConfig() {
        const baseConfig = {
            type: 'line',
            data: { datasets: [] },
            options: {
                responsive: this.config.responsive,
                maintainAspectRatio: this.config.maintainAspectRatio,
                animation: this.config.animation,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                plugins: {
                    legend: {
                        position: 'top'
                    }
                }
            }
        };

        // Configure scales based on chart type
        switch (this.config.type) {
            case 'realtime':
            case 'static':
                baseConfig.options.scales = this.createTimeScales();
                baseConfig.options.plugins.annotation = {
                    annotations: {}
                };
                break;
                
            case 'database':
                baseConfig.options.scales = this.createDatabaseScales();
                break;
                
            case 'setup':
                baseConfig.options.scales = this.createSetupScales();
                baseConfig.options.onClick = (event) => this.handleChartClick(event);
                break;
        }

        return baseConfig;
    }

    /**
     * Create time-based scales for real-time charts
     */
    createTimeScales() {
        return {
            x: {
                type: 'linear',
                position: 'bottom',
                min: 0,
                max: 300, // 5 minutes default
                title: {
                    display: true,
                    text: 'Time (seconds)',
                    font: { size: 14 }
                },
                ticks: {
                    callback: (value) => {
                        if (this.startTime) {
                            const timestamp = new Date(this.startTime + value * 1000);
                            return formatTime(timestamp);
                        }
                        return value;
                    }
                }
            },
            y: {
                title: {
                    display: true,
                    text: 'Temperature (°C)',
                    font: { size: 14 }
                },
                min: this.config.yMin || 0,
                max: this.config.yMax || 100
            }
        };
    }

    /**
     * Create scales for database viewer
     */
    createDatabaseScales() {
        return {
            x: {
                type: 'time',
                time: {
                    unit: 'second',
                    displayFormats: {
                        second: 'HH:mm:ss'
                    },
                    tooltipFormat: 'yyyy-MM-dd HH:mm:ss'
                },
                title: {
                    display: true,
                    text: 'Time'
                }
            },
            y: {
                title: {
                    display: true,
                    text: 'Value'
                },
                beginAtZero: false
            }
        };
    }

    /**
     * Create scales for setup/editor charts
     */
    createSetupScales() {
        return {
            x: {
                type: 'linear',
                position: 'bottom',
                min: 0,
                max: 120, // 2 hours default
                title: {
                    display: true,
                    text: 'Time (minutes)',
                    font: { size: 14 }
                }
            },
            y: {
                min: -20,
                max: 180,
                title: {
                    display: true,
                    text: 'Temperature (°C)',
                    font: { size: 14 }
                }
            }
        };
    }

    /**
     * Add a dataset to the chart
     */
    addDataset(dataset) {
        if (!this.chartInstance) return;
        
        const defaultDataset = {
            borderColor: getRandomColor(),
            backgroundColor: getRandomColor(0.1),
            fill: false,
            pointRadius: this.config.type === 'realtime' ? 1 : 4,
            tension: this.config.type === 'database' ? 0.3 : 0,
            ...dataset
        };
        
        this.chartInstance.data.datasets.push(defaultDataset);
        this.chartInstance.update();
    }

    /**
     * Update chart data (for real-time)
     */
    updateRealTimeData(data, elapsedSeconds, selectedSensors = new Set()) {
        if (!this.chartInstance || this.config.type !== 'realtime') return;

        // Update max elapsed time
        if (elapsedSeconds > this.maxElapsedSeconds) {
            this.maxElapsedSeconds = elapsedSeconds;
        }

        // Process sensor data
        Object.entries(data).forEach(([sensorName, value]) => {
            if (typeof value === 'number') {
                let dataset = this.chartInstance.data.datasets.find(ds => ds.label === sensorName);
                
                if (!dataset) {
                    dataset = {
                        label: sensorName,
                        data: [],
                        borderColor: getRandomColor(),
                        fill: false,
                        pointRadius: 1,
                        hidden: !selectedSensors.has(sensorName)
                    };
                    this.chartInstance.data.datasets.push(dataset);
                }
                
                dataset.data.push({ x: elapsedSeconds, y: value });
            }
        });

        // Update time axis
        this.updateTimeAxis(elapsedSeconds);
        this.chartInstance.update();
    }

    /**
     * Update time axis for real-time data
     */
    updateTimeAxis(elapsedSeconds) {
        if (!this.chartInstance) return;

        const currentMax = this.chartInstance.options.scales.x.max;
        if (elapsedSeconds >= currentMax) {
            this.chartInstance.options.scales.x.max = elapsedSeconds + 10;
        }

        // Ensure minimum 5-minute window
        if (this.chartInstance.options.scales.x.max < 300) {
            this.chartInstance.options.scales.x.max = 300;
        }
    }

    /**
     * Add desired path (for real-time charts)
     */
    addDesiredPath(desiredPath) {
        if (!this.chartInstance) return;

        if (!Array.isArray(desiredPath) || desiredPath.length === 1) {
            // Single temperature - add as horizontal line
            const desiredTemp = Array.isArray(desiredPath) ? desiredPath[0].y : desiredPath.y;
            this.chartInstance.options.plugins.annotation.annotations.desiredLine = {
                type: 'line',
                yMin: desiredTemp,
                yMax: desiredTemp,
                borderColor: 'red',
                borderWidth: 2,
                label: {
                    content: `Desired Temperature: ${desiredTemp}°C`,
                    enabled: true,
                    position: 'end'
                }
            };
        } else {
            // Temperature profile - add as dataset
            this.addDataset({
                label: 'Desired Graph',
                data: desiredPath.map(point => ({ x: point.x, y: point.y })),
                borderColor: 'red',
                borderWidth: 2,
                pointRadius: 1
            });
        }
        
        this.chartInstance.update();
    }

    /**
     * Setup interactive chart (for setup page)
     */
    setupInteractiveChart() {
        if (this.config.type !== 'setup') return;
        
        // Initialize with empty dataset
        this.addDataset({
            label: 'Temperature Profile',
            data: [],
            borderColor: 'rgba(75, 192, 192, 1)',
            backgroundColor: 'rgba(75, 192, 192, 0.1)',
            borderWidth: 2,
            pointRadius: 6,
            pointHoverRadius: 8
        });

        // Load temperature limits and add annotations
        this.loadTemperatureLimits();
    }

    /**
     * Load temperature limits from server and add red zone annotations
     */
    async loadTemperatureLimits() {
        if (this.config.type !== 'setup' || !this.chartInstance) return;

        try {
            const response = await fetch('/get_graph_min_max_temp');
            if (!response.ok) {
                console.warn('Could not fetch temperature limits');
                return;
            }
            
            const data = await response.json();
            const { min_temp, max_temp } = data;
            
            if (min_temp !== undefined && max_temp !== undefined) {
                this.addTemperatureLimitAnnotations(min_temp, max_temp);
            }
        } catch (error) {
            console.warn('Error fetching temperature limits:', error);
        }
    }

    /**
     * Add red zone annotations for temperature limits
     */
    addTemperatureLimitAnnotations(minTemp, maxTemp) {
        if (!this.chartInstance || !this.chartInstance.options.plugins) return;

        // Initialize annotation plugin if not present
        if (!this.chartInstance.options.plugins.annotation) {
            this.chartInstance.options.plugins.annotation = {
                annotations: {}
            };
        }

        const yMin = this.chartInstance.options.scales.y.min || -20;
        const yMax = this.chartInstance.options.scales.y.max || 180;

        // Add red zone below minimum temperature
        if (minTemp > yMin) {
            this.chartInstance.options.plugins.annotation.annotations.redZoneLow = {
                type: 'box',
                xMin: 0,
                xMax: this.chartInstance.options.scales.x.max || 120,
                yMin: yMin,
                yMax: minTemp,
                backgroundColor: 'rgba(255, 0, 0, 0.15)',
                borderColor: 'rgba(255, 0, 0, 0.3)',
                borderWidth: 1,
                label: {
                    enabled: true,
                    content: `Below Min (${minTemp}°C)`,
                    position: 'center',
                    color: 'rgba(255, 0, 0, 0.8)',
                    font: {
                        size: 12,
                        weight: 'bold'
                    }
                }
            };
        }

        // Add red zone above maximum temperature
        if (maxTemp < yMax) {
            this.chartInstance.options.plugins.annotation.annotations.redZoneHigh = {
                type: 'box',
                xMin: 0,
                xMax: this.chartInstance.options.scales.x.max || 120,
                yMin: maxTemp,
                yMax: yMax,
                backgroundColor: 'rgba(255, 0, 0, 0.15)',
                borderColor: 'rgba(255, 0, 0, 0.3)',
                borderWidth: 1,
                label: {
                    enabled: true,
                    content: `Above Max (${maxTemp}°C)`,
                    position: 'center',
                    color: 'rgba(255, 0, 0, 0.8)',
                    font: {
                        size: 12,
                        weight: 'bold'
                    }
                }
            };
        }

        // Add boundary lines for clearer visualization
        this.chartInstance.options.plugins.annotation.annotations.minTempLine = {
            type: 'line',
            yMin: minTemp,
            yMax: minTemp,
            borderColor: 'rgba(255, 0, 0, 0.6)',
            borderWidth: 2,
            borderDash: [5, 5],
            label: {
                enabled: true,
                content: `Min: ${minTemp}°C`,
                position: 'end',
                backgroundColor: 'rgba(255, 0, 0, 0.8)',
                color: 'white',
                font: {
                    size: 11,
                    weight: 'bold'
                }
            }
        };

        this.chartInstance.options.plugins.annotation.annotations.maxTempLine = {
            type: 'line',
            yMin: maxTemp,
            yMax: maxTemp,
            borderColor: 'rgba(255, 0, 0, 0.6)',
            borderWidth: 2,
            borderDash: [5, 5],
            label: {
                enabled: true,
                content: `Max: ${maxTemp}°C`,
                position: 'end',
                backgroundColor: 'rgba(255, 0, 0, 0.8)',
                color: 'white',
                font: {
                    size: 11,
                    weight: 'bold'
                }
            }
        };

        // Update chart to show annotations
        this.chartInstance.update();
    }

    /**
     * Update the x range of temperature limit annotations when x-axis extends
     */
    updateTemperatureLimitAnnotationsXRange(newMaxX) {
        if (!this.chartInstance || !this.chartInstance.options.plugins?.annotation?.annotations) return;

        const annotations = this.chartInstance.options.plugins.annotation.annotations;
        
        // Update red zone annotations with new x range
        if (annotations.redZoneLow) {
            annotations.redZoneLow.xMax = newMaxX;
        }
        
        if (annotations.redZoneHigh) {
            annotations.redZoneHigh.xMax = newMaxX;
        }
        
        console.log(`[ChartManager] Temperature limit annotations updated to x-max: ${newMaxX}`);
    }

    /**
     * Handle chart click (for setup page)
     */
    handleChartClick(event) {
        if (this.config.type !== 'setup') return;

        const canvasPosition = Chart.helpers.getRelativePosition(event, this.chartInstance);
        const x = this.chartInstance.scales.x.getValueForPixel(canvasPosition.x);
        const y = this.chartInstance.scales.y.getValueForPixel(canvasPosition.y);

        // Round to reasonable increments
        const roundedX = Math.round(x / 5) * 5;
        const roundedY = Math.round(y);

        // Note: addPoint() will handle dynamic x-axis scaling automatically
        this.addPoint(roundedX, roundedY);
    }

    /**
     * Add point (for setup page)
     */
    addPoint(x, y) {
        if (this.config.type !== 'setup') return;

        // Get current x-axis maximum
        const currentMaxX = this.chartInstance.options.scales.x.max;
        const threeFourthsPoint = currentMaxX * 0.75;
        
        // Validate minimum ranges
        if (x < 0) {
            alert('Time must be greater than 0 minutes');
            return;
        }
        if (y < -20 || y > 180) {
            alert('Temperature must be between -20 and 180°C');
            return;
        }

        // Dynamic x-axis scaling: extend if point is past 3/4 of current range
        if (x > threeFourthsPoint) {
            // Calculate new maximum - extend by 50% or ensure at least 20 minutes beyond the new point
            const extensionOption1 = currentMaxX * 1.5;
            const extensionOption2 = x + 20;
            const newMaxX = Math.max(extensionOption1, extensionOption2);
            
            // Update x-axis maximum
            this.chartInstance.options.scales.x.max = newMaxX;
            
            // Also update any temperature limit annotations to match new x range
            this.updateTemperatureLimitAnnotationsXRange(newMaxX);
            
            console.log(`[ChartManager] X-axis extended from ${currentMaxX} to ${newMaxX} minutes (point at ${x} minutes)`);
        }

        // Check for duplicate time points
        const existingIndex = this.points.findIndex(point => point.x === x);
        if (existingIndex !== -1) {
            this.points[existingIndex].y = y;
        } else {
            this.points.push({ x, y });
        }

        this.updateSetupChart();
        this.unsavedChanges = true;
        
        // Call callback if set
        if (this.onPointAddedCallback) {
            this.onPointAddedCallback();
        }
    }

    /**
     * Update setup chart
     */
    updateSetupChart() {
        if (this.config.type !== 'setup' || !this.chartInstance) return;

        // Sort points by time
        this.points.sort((a, b) => a.x - b.x);
        
        // Update chart data
        this.chartInstance.data.datasets[0].data = [...this.points];
        this.chartInstance.update('none');
    }

    /**
     * Clear chart data
     */
    clearData() {
        if (!this.chartInstance) return;

        if (this.config.type === 'realtime') {
            // Keep only desired path
            this.chartInstance.data.datasets = this.chartInstance.data.datasets.filter(
                dataset => dataset.label === 'Desired Graph'
            );
            
            // Remove start time line
            if (this.startTimeLineConfig && this.chartInstance.options.plugins.annotation) {
                delete this.chartInstance.options.plugins.annotation.annotations.startTimeLine;
                this.startTimeLineConfig = null;
            }
        } else {
            this.chartInstance.data.datasets.forEach(dataset => dataset.data = []);
            if (this.config.type === 'setup') {
                this.points = [];
                this.unsavedChanges = false;
            }
        }
        
        this.chartInstance.update();
    }

    /**
     * Update dataset visibility
     */
    updateDatasetVisibility(sensorName, isVisible) {
        if (!this.chartInstance) return;

        const dataset = this.chartInstance.data.datasets.find(ds => ds.label === sensorName);
        if (dataset) {
            dataset.hidden = !isVisible;
            this.chartInstance.update();
        }
    }

    /**
     * Load database data
     */
    loadDatabaseData(datasets) {
        if (!this.chartInstance || this.config.type !== 'database') return;

        this.chartInstance.data.datasets = datasets;
        this.chartInstance.update();
    }

    /**
     * Set start time (for real-time charts)
     */
    setStartTime(startTime) {
        this.startTime = startTime;
        if (this.chartInstance && this.chartInstance.options.scales.x.ticks) {
            this.chartInstance.options.scales.x.ticks.callback = (value) => {
                const timestamp = new Date(startTime + value * 1000);
                return formatTime(timestamp);
            };
        }
    }

    /**
     * Reset elapsed time counter
     */
    resetMaxElapsedTime() {
        this.maxElapsedSeconds = 0;
    }

    /**
     * Get chart instance
     */
    getChart() {
        return this.chartInstance;
    }

    /**
     * Setup zoom functionality for database charts
     */
    setupZoomFunctionality() {
        if (this.config.type !== 'database' || !this.chartInstance) return;
        
        const canvas = this.chartInstance.canvas;
        
        // Store original limits
        this.originalXLimits = {
            min: this.chartInstance.options.scales.x.min,
            max: this.chartInstance.options.scales.x.max
        };
        
        // Mouse event handlers
        canvas.addEventListener('mousedown', (e) => this.handleMouseDown(e));
        canvas.addEventListener('mousemove', (e) => this.handleMouseMove(e));
        canvas.addEventListener('mouseup', (e) => this.handleMouseUp(e));
        canvas.addEventListener('mouseleave', (e) => this.handleMouseLeave(e));
        
        // Double-click to reset zoom
        canvas.addEventListener('dblclick', (e) => this.resetZoom());
        
        // Disable default context menu to prevent interference
        canvas.addEventListener('contextmenu', (e) => e.preventDefault());
        
        // Create selection overlay
        this.createSelectionOverlay();
    }
    
    /**
     * Create selection overlay for drag selection
     */
    createSelectionOverlay() {
        if (!this.chartInstance) return;
        
        const canvas = this.chartInstance.canvas;
        const container = canvas.parentElement;
        
        // Create overlay div
        this.selectionOverlay = document.createElement('div');
        this.selectionOverlay.style.cssText = `
            position: absolute;
            border: 2px dashed #007bff;
            background: rgba(0, 123, 255, 0.1);
            pointer-events: none;
            display: none;
            z-index: 10;
        `;
        
        // Position relative to container
        if (container.style.position !== 'relative' && container.style.position !== 'absolute') {
            container.style.position = 'relative';
        }
        
        container.appendChild(this.selectionOverlay);
    }
    
    /**
     * Handle mouse down event for drag selection
     */
    handleMouseDown(e) {
        if (this.config.type !== 'database' || !this.chartInstance) return;
        
        // Only start drag on left mouse button
        if (e.button !== 0) return;
        
        const rect = this.chartInstance.canvas.getBoundingClientRect();
        const canvasPosition = Chart.helpers.getRelativePosition(e, this.chartInstance);
        
        // Check if click is within the plot area
        const chartArea = this.chartInstance.chartArea;
        if (canvasPosition.x < chartArea.left || canvasPosition.x > chartArea.right ||
            canvasPosition.y < chartArea.top || canvasPosition.y > chartArea.bottom) {
            return;
        }
        
        this.isDragging = true;
        this.dragStart = {
            x: canvasPosition.x,
            y: canvasPosition.y,
            screenX: e.clientX - rect.left,
            screenY: e.clientY - rect.top
        };
        
        // Prevent text selection
        e.preventDefault();
    }
    
    /**
     * Handle mouse move event for drag selection
     */
    handleMouseMove(e) {
        if (!this.isDragging || this.config.type !== 'database' || !this.chartInstance) return;
        
        const rect = this.chartInstance.canvas.getBoundingClientRect();
        const canvasPosition = Chart.helpers.getRelativePosition(e, this.chartInstance);
        
        this.dragEnd = {
            x: canvasPosition.x,
            y: canvasPosition.y,
            screenX: e.clientX - rect.left,
            screenY: e.clientY - rect.top
        };
        
        // Update selection overlay
        this.updateSelectionOverlay();
    }
    
    /**
     * Handle mouse up event for drag selection
     */
    handleMouseUp(e) {
        if (!this.isDragging || this.config.type !== 'database' || !this.chartInstance) return;
        
        this.isDragging = false;
        
        if (this.dragStart && this.dragEnd) {
            this.performZoom();
        }
        
        // Hide selection overlay
        if (this.selectionOverlay) {
            this.selectionOverlay.style.display = 'none';
        }
        
        // Clear drag data
        this.dragStart = null;
        this.dragEnd = null;
    }
    
    /**
     * Handle mouse leave event
     */
    handleMouseLeave(e) {
        if (this.isDragging) {
            this.isDragging = false;
            if (this.selectionOverlay) {
                this.selectionOverlay.style.display = 'none';
            }
            this.dragStart = null;
            this.dragEnd = null;
        }
    }
    
    /**
     * Update selection overlay position and size
     */
    updateSelectionOverlay() {
        if (!this.selectionOverlay || !this.dragStart || !this.dragEnd) return;
        
        const startX = Math.min(this.dragStart.screenX, this.dragEnd.screenX);
        const endX = Math.max(this.dragStart.screenX, this.dragEnd.screenX);
        const width = endX - startX;
        
        // Only show overlay if there's significant horizontal movement
        if (width > 5) {
            const chartArea = this.chartInstance.chartArea;
            const canvas = this.chartInstance.canvas;
            
            // Get the canvas position relative to its container
            const canvasOffsetTop = canvas.offsetTop;
            const canvasOffsetLeft = canvas.offsetLeft;
            
            this.selectionOverlay.style.display = 'block';
            this.selectionOverlay.style.left = `${canvasOffsetLeft + startX}px`;
            this.selectionOverlay.style.top = `${canvasOffsetTop + chartArea.top}px`;
            this.selectionOverlay.style.width = `${width}px`;
            this.selectionOverlay.style.height = `${chartArea.bottom - chartArea.top}px`;
        } else {
            this.selectionOverlay.style.display = 'none';
        }
    }
    
    /**
     * Perform zoom based on selection
     */
    performZoom() {
        if (!this.dragStart || !this.dragEnd || !this.chartInstance) return;
        
        // Calculate the selected time range
        const startX = Math.min(this.dragStart.x, this.dragEnd.x);
        const endX = Math.max(this.dragStart.x, this.dragEnd.x);
        
        // Convert pixel positions to data values
        const startValue = this.chartInstance.scales.x.getValueForPixel(startX);
        const endValue = this.chartInstance.scales.x.getValueForPixel(endX);
        
        // Only zoom if there's a reasonable selection
        if (Math.abs(endX - startX) > 10) {
            // Update chart x-axis limits
            this.chartInstance.options.scales.x.min = startValue;
            this.chartInstance.options.scales.x.max = endValue;
            this.chartInstance.update('none');
        }
    }
    
    /**
     * Reset zoom to original limits
     */
    resetZoom() {
        if (!this.chartInstance || this.config.type !== 'database') return;
        
        // Reset to original limits or auto-fit to data
        if (this.originalXLimits && (this.originalXLimits.min !== undefined || this.originalXLimits.max !== undefined)) {
            this.chartInstance.options.scales.x.min = this.originalXLimits.min;
            this.chartInstance.options.scales.x.max = this.originalXLimits.max;
        } else {
            // Auto-fit to data
            delete this.chartInstance.options.scales.x.min;
            delete this.chartInstance.options.scales.x.max;
        }
        
        this.chartInstance.update('none');
    }

    /**
     * Destroy chart
     */
    destroy() {
        // Clean up selection overlay
        if (this.selectionOverlay && this.selectionOverlay.parentElement) {
            this.selectionOverlay.parentElement.removeChild(this.selectionOverlay);
        }
        
        if (this.chartInstance) {
            this.chartInstance.destroy();
            this.chartInstance = null;
        }
    }
}