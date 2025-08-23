/**
 * Chart Manager - Real-time charts for manual control and display graph
 * Wrapper around Universal Chart Manager for compatibility
 */

import UniversalChartManager from './universal-chart-manager.js';

export default class ChartManager {
  constructor(sensorGraph) {
    this.sensorGraph = sensorGraph;
    this.universalManager = new UniversalChartManager({
      canvasId: 'newGraph',
      type: 'realtime'
    });
  }

  /**
   * Creates chart configuration with appropriate options
   * @param {Object} config - Chart configuration data
   * @returns {Object} Chart configuration object
   */
  createChartConfig(config = {}) {
    // This method is kept for compatibility but delegates to universal manager
    return this.universalManager.createChartConfig();
  }

  /**
   * Renders the graph with initial data
   * @param {Object} response - Initial graph data
   */
  renderGraph(response) {
    const { desired_path: desiredPath, data: graphData, config } = response;

    // Initialize the chart
    this.universalManager.init();
    
    // Set start time
    if (this.sensorGraph.startTime) {
      this.universalManager.setStartTime(this.sensorGraph.startTime);
    }

    // Add desired path if provided
    if (desiredPath) {
      this.universalManager.addDesiredPath(desiredPath);
    }
  }

  /**
   * Updates the chart's time axis based on the current start time
   * @param {number} startTime - The timestamp when recording started
   */
  updateChartTimeAxis(startTime) {
    this.universalManager.setStartTime(startTime);
  }

  /**
   * Updates the chart's x-axis range based on incoming data
   * @param {number} elapsedSeconds - Current elapsed time in seconds
   */
  updateChartXAxisRange(elapsedSeconds) {
    // Handled internally by universal manager
    this.universalManager.updateTimeAxis(elapsedSeconds);
  }

  /**
   * Updates chart data with new sensor readings
   * @param {Object} data - Sensor data
   * @param {number} elapsedSeconds - Elapsed time in seconds
   * @param {Set} selectedSensors - Currently selected Sensors
   * @param {Object} guardingInfo - Guarding service information
   */
  updateChartData(data, elapsedSeconds, selectedSensors, guardingInfo = null) {
    this.universalManager.updateRealTimeData(data, elapsedSeconds, selectedSensors, guardingInfo);
  }

  /**
   * Updates dataset visibility based on sensor selection
   * @param {string} sensorName - Name of the sensor
   * @param {boolean} isVisible - Whether the sensor should be visible
   */
  updateDatasetVisibility(sensorName, isVisible) {
    this.universalManager.updateDatasetVisibility(sensorName, isVisible);
  }

  /**
   * Clears all sensor data from the chart while preserving the desired path
   */
  clearChartData() {
    this.universalManager.clearData();
  }

  /**
   * Resets the max elapsed time counter
   */
  resetMaxElapsedTime() {
    this.universalManager.resetMaxElapsedTime();
  }

  /**
   * Adds desired temperature path to the chart
   * @param {Array|Object} desiredPath - Desired temperature data
   */
  addDesiredPath(desiredPath) {
    this.universalManager.addDesiredPath(desiredPath);
  }

  /**
   * Get the underlying chart instance
   */
  get chartInstance() {
    return this.universalManager.getChart();
  }

  /**
   * Get max elapsed seconds
   */
  get maxElapsedSeconds() {
    return this.universalManager.maxElapsedSeconds;
  }

  /**
   * Set max elapsed seconds
   */
  set maxElapsedSeconds(value) {
    this.universalManager.maxElapsedSeconds = value;
  }

  /**
   * Load existing cycle data into the chart
   * @param {Object} cycleData - The cycle data with sensor_data and calculation_data
   * @param {string} cycleStartTime - ISO timestamp of when the cycle started
   */
  loadExistingCycleData(cycleData, cycleStartTime) {
    this.universalManager.loadHistoricalData(cycleData, cycleStartTime);
  }
}