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
            // Performance optimization settings
            maxDataPoints: config.maxDataPoints || 2000, // Rolling window size
            decimationThreshold: config.decimationThreshold || 5000, // Start decimating after this many points
            batchUpdateInterval: config.batchUpdateInterval || 1000, // Batch updates every 1000ms
            enableBatchUpdates: config.enableBatchUpdates !== false,
            ...config
        };
        
        // Real-time specific properties
        this.startTime = null;
        this.maxElapsedSeconds = 0;
        this.startTimeLineConfig = null;
        
        // Static/setup specific properties
        this.points = []; // Store as {x: offsetSeconds, y: temperature}
        this.unsavedChanges = false;
        this.onPointAddedCallback = null;
        this.referenceStartTime = null; // Reference time for converting offsets to display times

        // Zoom functionality properties
        this.isDragging = false;
        this.dragStart = null;
        this.dragEnd = null;
        this.selectionOverlay = null;
        this.originalXLimits = null;

        // Performance optimization properties
        this.pendingDataUpdates = new Map(); // Store pending data updates for batch processing
        this.lastUpdateTime = 0;
        this.batchUpdateTimer = null;
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
        
        // Add zoom functionality for database and realtime charts
        if (this.config.type === 'database' || this.config.type === 'realtime') {
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
                max: this.config.xMax || 300, // Use dynamic xMax or 5 minutes default
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
        // Create base time starting at 00:00:00 for relative time display
        const baseTime = new Date(2000, 0, 1, 0, 0, 0); // January 1, 2000 00:00:00
        const twoHoursLater = new Date(baseTime.getTime() + 2 * 60 * 60 * 1000); // 2 hours from 00:00
        
        return {
            x: {
                type: 'time',
                position: 'bottom',
                min: baseTime,
                max: twoHoursLater,
                time: {
                    unit: 'minute',
                    displayFormats: {
                        minute: 'HH:mm',
                        hour: 'HH:mm'
                    },
                    tooltipFormat: 'HH:mm:ss'
                },
                title: {
                    display: true,
                    text: 'Cycle Time',
                    font: { size: 14 }
                },
                ticks: {
                    maxTicksLimit: 8,
                    major: {
                        enabled: true
                    }
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
     * Set the reference start time for offset calculations
     */
    setReferenceStartTime(startTime) {
        this.referenceStartTime = startTime || new Date();
        console.log(`[ChartManager] Reference start time set to: ${this.referenceStartTime.toLocaleString()}`);
    }

    /**
     * Convert offset seconds to relative datetime for display (starting from 00:00)
     */
    offsetToDateTime(offsetSeconds) {
        // Create a base date starting at 00:00:00 for relative time display
        const baseDate = new Date(2000, 0, 1, 0, 0, 0); // January 1, 2000 00:00:00
        return new Date(baseDate.getTime() + offsetSeconds * 1000);
    }

    /**
     * Convert relative datetime to offset seconds
     */
    dateTimeToOffset(dateTime) {
        const baseDate = new Date(2000, 0, 1, 0, 0, 0); // January 1, 2000 00:00:00
        const timestamp = dateTime instanceof Date ? dateTime.getTime() : new Date(dateTime).getTime();
        return (timestamp - baseDate.getTime()) / 1000;
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
    updateRealTimeData(data, elapsedSeconds, selectedSensors = new Set(), guardingInfo = null) {
        if (!this.chartInstance || this.config.type !== 'realtime') return;

        // Update max elapsed time
        if (elapsedSeconds > this.maxElapsedSeconds) {
            this.maxElapsedSeconds = elapsedSeconds;
        }

        // Use batch updates for better performance
        if (this.config.enableBatchUpdates) {
            this.addToPendingUpdates(data, elapsedSeconds, selectedSensors, guardingInfo);
            return;
        }

        // Direct update (fallback for immediate updates)
        this.processDataUpdate(data, elapsedSeconds, selectedSensors, guardingInfo);
    }

    /**
     * Add data to pending updates for batch processing
     */
    addToPendingUpdates(data, elapsedSeconds, selectedSensors, guardingInfo) {
        // Store the latest data for each sensor
        Object.entries(data).forEach(([sensorName, value]) => {
            if (typeof value === 'number') {
                this.pendingDataUpdates.set(sensorName, { x: elapsedSeconds, y: value });
            }
        });

        // Store guarding info (latest wins)
        this.pendingGuardingInfo = guardingInfo;

        // Set up batch update timer if not already running
        if (!this.batchUpdateTimer) {
            this.batchUpdateTimer = setTimeout(() => {
                this.processBatchUpdate(selectedSensors);
            }, this.config.batchUpdateInterval);
        }
    }

    /**
     * Process batched updates for better performance
     */
    processBatchUpdate(selectedSensors) {
        if (this.pendingDataUpdates.size === 0) {
            this.batchUpdateTimer = null;
            return;
        }

        // Process all pending updates
        this.pendingDataUpdates.forEach((dataPoint, sensorName) => {
            this.addDataPointToDataset(sensorName, dataPoint, selectedSensors);
        });

        // Handle guarding information
        this.handleGuardingInfo(this.pendingGuardingInfo);

        // Update time axis with latest elapsed time
        const latestTime = Math.max(...Array.from(this.pendingDataUpdates.values()).map(point => point.x));
        this.updateTimeAxis(latestTime);

        // Update chart with optimized mode
        this.chartInstance.update('none'); // Skip animations for better performance

        // Clear pending updates
        this.pendingDataUpdates.clear();
        this.pendingGuardingInfo = null;
        this.batchUpdateTimer = null;
    }

    /**
     * Process individual data update (direct mode)
     */
    processDataUpdate(data, elapsedSeconds, selectedSensors, guardingInfo) {
        // Process sensor data
        Object.entries(data).forEach(([sensorName, value]) => {
            if (typeof value === 'number') {
                this.addDataPointToDataset(sensorName, { x: elapsedSeconds, y: value }, selectedSensors);
            }
        });

        // Handle guarding information
        this.handleGuardingInfo(guardingInfo);

        // Update time axis
        this.updateTimeAxis(elapsedSeconds);
        this.chartInstance.update('none');
    }

    /**
     * Add data point to dataset with rolling window optimization
     */
    addDataPointToDataset(sensorName, dataPoint, selectedSensors) {
        let dataset = this.chartInstance.data.datasets.find(ds => ds.label === sensorName);

        if (!dataset) {
            dataset = {
                label: sensorName,
                data: [],
                borderColor: getRandomColor(),
                fill: false,
                pointRadius: 0, // Disable point markers for better performance
                borderWidth: 1,
                hidden: !selectedSensors.has(sensorName)
            };
            this.chartInstance.data.datasets.push(dataset);
        }

        // Add new data point
        dataset.data.push(dataPoint);

        // Apply rolling window to limit memory usage
        if (dataset.data.length > this.config.maxDataPoints) {
            // Apply decimation if above threshold
            if (dataset.data.length > this.config.decimationThreshold) {
                dataset.data = this.decimateData(dataset.data, this.config.maxDataPoints);
            } else {
                // Simple rolling window - remove oldest points
                dataset.data = dataset.data.slice(-this.config.maxDataPoints);
            }
        }
    }

    /**
     * Decimate data using Largest Triangle Three Buckets (LTTB) algorithm
     */
    decimateData(data, targetPoints) {
        if (data.length <= targetPoints) return data;

        // Always keep first and last points
        if (targetPoints <= 2) return [data[0], data[data.length - 1]];

        const bucketSize = (data.length - 2) / (targetPoints - 2);
        const decimated = [data[0]]; // Always keep first point

        let bucketIndex = 1;
        let nextBucketIndex = Math.floor(bucketIndex + bucketSize);

        for (let i = 1; i < targetPoints - 1; i++) {
            // Calculate points for triangle area calculation
            const pointA = decimated[decimated.length - 1];

            // Get average point in next bucket for triangle calculation
            let avgX = 0, avgY = 0, avgRangeStart = Math.floor(nextBucketIndex);
            let avgRangeEnd = Math.min(Math.floor(nextBucketIndex + bucketSize), data.length);

            for (let j = avgRangeStart; j < avgRangeEnd; j++) {
                avgX += data[j].x;
                avgY += data[j].y;
            }
            avgX /= (avgRangeEnd - avgRangeStart);
            avgY /= (avgRangeEnd - avgRangeStart);

            // Find the point in current bucket that forms largest triangle
            let maxArea = 0;
            let maxAreaIndex = Math.floor(bucketIndex);
            const currentBucketStart = Math.floor(bucketIndex);
            const currentBucketEnd = Math.min(Math.floor(bucketIndex + bucketSize), data.length);

            for (let j = currentBucketStart; j < currentBucketEnd; j++) {
                const pointB = data[j];
                const area = Math.abs(
                    (pointA.x - avgX) * (pointB.y - pointA.y) -
                    (pointA.x - pointB.x) * (avgY - pointA.y)
                );

                if (area > maxArea) {
                    maxArea = area;
                    maxAreaIndex = j;
                }
            }

            decimated.push(data[maxAreaIndex]);
            bucketIndex = nextBucketIndex;
            nextBucketIndex = Math.floor(bucketIndex + bucketSize);
        }

        decimated.push(data[data.length - 1]); // Always keep last point
        return decimated;
    }

    /**
     * Handle guarding information and apply visual effects
     */
    handleGuardingInfo(guardingInfo) {
        if (!this.chartInstance || !guardingInfo) return;

        const chartCanvas = this.chartInstance.canvas;
        const chartContainer = chartCanvas.parentElement;

        if (guardingInfo.is_guarding) {
            // Apply red flashing effect
            this.startGuardingFlash(chartContainer, guardingInfo);
        } else {
            // Remove guarding effects
            this.stopGuardingFlash(chartContainer);
        }
    }

    /**
     * Start the guarding notification (no flashing effect)
     */
    startGuardingFlash(chartContainer, guardingInfo) {
        // Add guarding class for positioning
        chartContainer.classList.add('guarding-active');
        
        // Create or update guarding notification
        this.updateGuardingNotification(guardingInfo);
    }

    /**
     * Stop the guarding notification
     */
    stopGuardingFlash(chartContainer) {
        chartContainer.classList.remove('guarding-active');
        
        // Remove guarding notification from document body
        const notification = document.querySelector('.guarding-notification');
        if (notification) {
            notification.remove();
        }
    }

    /**
     * Create or update the guarding notification display
     */
    updateGuardingNotification(guardingInfo) {
        let notification = document.querySelector('.guarding-notification');
        
        if (!notification) {
            notification = document.createElement('div');
            notification.className = 'guarding-notification';
            document.body.appendChild(notification);
        }

        // Create reason messages
        const reasonMessages = guardingInfo.reasons.map(reason => reason.message).join(', ');
        const statusMessage = guardingInfo.stop_steering_temperature && guardingInfo.stop_steering_current 
            ? 'Temperature & Current Limits Exceeded' 
            : guardingInfo.stop_steering_temperature 
            ? 'Temperature Limit Exceeded' 
            : 'Current Limit Exceeded';

        notification.innerHTML = `
            <div class="guarding-title">⚠️ STEERING DISABLED</div>
            <div class="guarding-status">${statusMessage}</div>
            <div class="guarding-reasons">${reasonMessages}</div>
        `;
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
                xMin: this.chartInstance.options.scales.x.min,
                xMax: this.chartInstance.options.scales.x.max,
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
                xMin: this.chartInstance.options.scales.x.min,
                xMax: this.chartInstance.options.scales.x.max,
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
    updateTemperatureLimitAnnotationsXRange() {
        if (!this.chartInstance || !this.chartInstance.options.plugins?.annotation?.annotations) return;

        const annotations = this.chartInstance.options.plugins.annotation.annotations;
        const currentMinX = this.chartInstance.options.scales.x.min;
        const currentMaxX = this.chartInstance.options.scales.x.max;
        
        // Update red zone annotations with new x range
        if (annotations.redZoneLow) {
            annotations.redZoneLow.xMin = currentMinX;
            annotations.redZoneLow.xMax = currentMaxX;
        }
        
        if (annotations.redZoneHigh) {
            annotations.redZoneHigh.xMin = currentMinX;
            annotations.redZoneHigh.xMax = currentMaxX;
        }
        
        console.log(`[ChartManager] Temperature limit annotations updated to range: ${currentMinX} - ${currentMaxX}`);
    }

    /**
     * Handle chart click (for setup page)
     */
    handleChartClick(event) {
        if (this.config.type !== 'setup') return;

        const canvasPosition = Chart.helpers.getRelativePosition(event, this.chartInstance);
        const x = this.chartInstance.scales.x.getValueForPixel(canvasPosition.x);
        const y = this.chartInstance.scales.y.getValueForPixel(canvasPosition.y);

        // x is a timestamp, convert to offset seconds and round to nearest minute (60 seconds)
        const offsetSeconds = this.dateTimeToOffset(new Date(x));
        const roundedOffsetSeconds = Math.round(offsetSeconds / 60) * 60;
        const roundedY = Math.round(y);

        // Note: addPoint() will handle dynamic x-axis scaling automatically
        this.addPoint(roundedOffsetSeconds, roundedY);
    }

    /**
     * Add point (for setup page)
     */
    addPoint(x, y) {
        if (this.config.type !== 'setup') return;

        // x should be offset seconds, convert if it's a Date
        const offsetSeconds = (x instanceof Date) ? this.dateTimeToOffset(x) : x;
        
        // Validate ranges
        if (offsetSeconds < 0) {
            alert('Time must be after the start time');
            return;
        }
        if (y < -20 || y > 180) {
            alert('Temperature must be between -20 and 180°C');
            return;
        }

        // Dynamic x-axis scaling: extend if point approaches current maximum
        const currentMinX = new Date(this.chartInstance.options.scales.x.min);
        const currentMaxX = new Date(this.chartInstance.options.scales.x.max);
        const pointDateTime = this.offsetToDateTime(offsetSeconds);
        
        const currentRange = currentMaxX.getTime() - currentMinX.getTime();
        const threeFourthsPoint = new Date(currentMinX.getTime() + currentRange * 0.75);
        
        if (pointDateTime > threeFourthsPoint) {
            // Extend by 50% of current range or at least 30 minutes beyond the new point
            const extensionOption1 = new Date(currentMaxX.getTime() + currentRange * 0.5);
            const extensionOption2 = new Date(pointDateTime.getTime() + 30 * 60 * 1000); // 30 minutes
            const newMaxX = new Date(Math.max(extensionOption1.getTime(), extensionOption2.getTime()));
            
            // Update x-axis maximum
            this.chartInstance.options.scales.x.max = newMaxX;
            
            // Update temperature limit annotations to match new range
            this.updateTemperatureLimitAnnotationsXRange();
            
            console.log(`[ChartManager] X-axis extended to ${newMaxX.toLocaleTimeString()} (point at ${pointDateTime.toLocaleTimeString()})`);
        }

        // Check for duplicate time points (within 1 minute tolerance)
        const existingIndex = this.points.findIndex(point => Math.abs(point.x - offsetSeconds) < 60);
        
        if (existingIndex !== -1) {
            this.points[existingIndex] = { x: offsetSeconds, y };
        } else {
            this.points.push({ x: offsetSeconds, y });
        }

        // Update chart with dynamic scaling
        this.updateSetupChart();
        this.updateDynamicScaling();
        this.unsavedChanges = true;
        
        // Call callback if set
        if (this.onPointAddedCallback) {
            this.onPointAddedCallback();
        }
    }

    /**
     * Update dynamic scaling based on setpoint data
     */
    updateDynamicScaling() {
        if (this.config.type !== 'setup' || !this.chartInstance || this.points.length === 0) return;

        // Find min and max offset seconds in the data
        const offsetSeconds = this.points.map(point => point.x);
        const minOffset = Math.min(...offsetSeconds);
        const maxOffset = Math.max(...offsetSeconds);
        
        // Calculate appropriate range (at least 2 hours, but expand as needed)
        const dataRange = maxOffset - minOffset;
        const minRange = 2 * 60 * 60; // 2 hours in seconds
        const padding = Math.max(minRange * 0.1, dataRange * 0.1); // 10% padding
        
        // Convert back to relative datetime for chart display
        const newMinX = this.offsetToDateTime(Math.max(0, minOffset - padding)); // Don't go before 00:00
        const newMaxX = this.offsetToDateTime(Math.max(maxOffset + padding, minRange));
        
        // Update chart scales
        this.chartInstance.options.scales.x.min = newMinX;
        this.chartInstance.options.scales.x.max = newMaxX;
        
        // Update temperature limit annotations to match new range
        this.updateTemperatureLimitAnnotationsXRange();
        
        console.log(`[ChartManager] Dynamic scaling: ${newMinX.toLocaleTimeString()} to ${newMaxX.toLocaleTimeString()}`);
    }

    /**
     * Update setup chart
     */
    updateSetupChart() {
        if (this.config.type !== 'setup' || !this.chartInstance) return;

        // Sort points by offset seconds
        this.points.sort((a, b) => a.x - b.x);
        
        // Convert offset seconds to datetime for chart display
        const displayPoints = this.points.map(point => ({
            x: this.offsetToDateTime(point.x),
            y: point.y
        }));
        
        // Update chart data
        this.chartInstance.data.datasets[0].data = displayPoints;
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
     * Setup zoom functionality for database and realtime charts
     */
    setupZoomFunctionality() {
        if ((this.config.type !== 'database' && this.config.type !== 'realtime') || !this.chartInstance) return;
        
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
        if ((this.config.type !== 'database' && this.config.type !== 'realtime') || !this.chartInstance) return;
        
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
        if (!this.isDragging || (this.config.type !== 'database' && this.config.type !== 'realtime') || !this.chartInstance) return;
        
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
        if (!this.isDragging || (this.config.type !== 'database' && this.config.type !== 'realtime') || !this.chartInstance) return;
        
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
        
        // Calculate the selected range
        const startX = Math.min(this.dragStart.x, this.dragEnd.x);
        const endX = Math.max(this.dragStart.x, this.dragEnd.x);
        const startY = Math.min(this.dragStart.y, this.dragEnd.y);
        const endY = Math.max(this.dragStart.y, this.dragEnd.y);
        
        // Convert pixel positions to data values
        const startXValue = this.chartInstance.scales.x.getValueForPixel(startX);
        const endXValue = this.chartInstance.scales.x.getValueForPixel(endX);
        
        // Only zoom if there's a reasonable selection
        if (Math.abs(endX - startX) > 10) {
            // For realtime charts, ensure we don't zoom past the starting point (time 0)
            let finalStartValue = startXValue;
            let finalEndValue = endXValue;
            
            if (this.config.type === 'realtime') {
                finalStartValue = Math.max(0, startXValue);
                finalEndValue = Math.max(0, endXValue);
                
                // If both values would be negative, don't zoom
                if (startXValue < 0 && endXValue < 0) {
                    return;
                }
            }
            
            // Update chart x-axis limits only
            this.chartInstance.options.scales.x.min = finalStartValue;
            this.chartInstance.options.scales.x.max = finalEndValue;
            this.chartInstance.update('none');
        }
    }
    
    /**
     * Reset zoom to original limits
     */
    resetZoom() {
        if (!this.chartInstance || (this.config.type !== 'database' && this.config.type !== 'realtime')) return;
        
        // Reset X-axis to original limits or auto-fit to data
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
     * Load historical cycle data into the chart
     * @param {Object} cycleData - Historical cycle data with sensor_data and calculation_data
     * @param {string} cycleStartTime - ISO timestamp of when the cycle started
     */
    loadHistoricalData(cycleData, cycleStartTime) {
        if (!this.chartInstance || this.config.type !== 'realtime') return;

        const { sensor_data, calculation_data } = cycleData;
        const cycleStart = new Date(cycleStartTime).getTime();
        
        // Process temperature sensor data
        if (sensor_data && sensor_data.temperature && sensor_data.temperature[0]) {
            sensor_data.temperature[0].forEach(([sensorId, timestamp, value]) => {
                if (typeof value === 'number') {
                    let dataset = this.chartInstance.data.datasets.find(ds => ds.label === sensorId);
                    
                    if (!dataset) {
                        dataset = {
                            label: sensorId,
                            data: [],
                            borderColor: getRandomColor(),
                            fill: false,
                            pointRadius: 1
                        };
                        this.chartInstance.data.datasets.push(dataset);
                    }
                    
                    // Convert timestamp to elapsed seconds from cycle start
                    const dataTime = new Date(timestamp).getTime();
                    const elapsedSeconds = Math.floor((dataTime - cycleStart) / 1000);
                    
                    dataset.data.push({ x: elapsedSeconds, y: value });
                }
            });
        }
        
        // Process current sensor data
        if (sensor_data && sensor_data.current && sensor_data.current[0]) {
            sensor_data.current[0].forEach(([sensorId, timestamp, value]) => {
                if (typeof value === 'number') {
                    let dataset = this.chartInstance.data.datasets.find(ds => ds.label === sensorId);
                    
                    if (!dataset) {
                        dataset = {
                            label: sensorId,
                            data: [],
                            borderColor: getRandomColor(),
                            fill: false,
                            pointRadius: 1
                        };
                        this.chartInstance.data.datasets.push(dataset);
                    }
                    
                    const dataTime = new Date(timestamp).getTime();
                    const elapsedSeconds = Math.floor((dataTime - cycleStart) / 1000);
                    
                    dataset.data.push({ x: elapsedSeconds, y: value });
                }
            });
        }
        
        // Update max elapsed time based on loaded data
        this.chartInstance.data.datasets.forEach(dataset => {
            if (dataset.data && dataset.data.length > 0) {
                const maxX = Math.max(...dataset.data.map(point => point.x));
                if (maxX > this.maxElapsedSeconds) {
                    this.maxElapsedSeconds = maxX;
                }
            }
        });
        
        // Update time axis to accommodate the data
        this.updateTimeAxis(this.maxElapsedSeconds);
        this.chartInstance.update();
    }

    /**
     * Destroy chart
     */
    destroy() {
        // Clean up batch update timer
        if (this.batchUpdateTimer) {
            clearTimeout(this.batchUpdateTimer);
            this.batchUpdateTimer = null;
        }

        // Clean up pending updates
        this.pendingDataUpdates.clear();
        this.pendingGuardingInfo = null;

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