import { formatTime, getRandomColor } from './utils.js';

/**
 * ChartManager handles all chart creation, rendering and updates
 */
export default class ChartManager {
  constructor(sensorGraph) {
    this.sensorGraph = sensorGraph;
    this.chartInstance = null;
    this.maxElapsedSeconds = 0;
    this.startTimeLineConfig = null;
    this.isStartTimeLineVisible = false;
  }

  /**
   * Creates chart configuration with appropriate options
   * @param {Object} config - Chart configuration data
   * @returns {Object} Chart configuration object
   */
  createChartConfig(config = {}) {
    const startTime = this.sensorGraph.startTime;

    const chartConfig = {
      type: 'line',
      data: {
        datasets: []
      },
      options: {
        responsive: true,
        animation: false,
        scales: {
          x: {
            type: 'linear',
            position: 'bottom',
            min: 0,
            max: 300, // Start with 5 minutes (300 seconds) as default
            ticks: {
              callback: (value) => {
                const timestamp = new Date(startTime + value * 1000);
                return formatTime(timestamp);
              }
            }
          },
          y: {
            min: 0,
            max: config.maxY || 100
          }
        },
        plugins: {
          legend: {
            position: 'top'
          },
          annotation: {
            annotations: {}
          }
        }
      }
    };

    return chartConfig;
  }

  /**
   * Renders the graph with initial data
   * @param {Object} response - Initial graph data
   */
  renderGraph(response) {
    const ctx = document.getElementById('newGraph').getContext('2d');
    const { desired_path: desiredPath, data: graphData, config } = response;

    if (this.chartInstance) {
      this.chartInstance.destroy();
    }

    const chartConfig = this.createChartConfig(config);
    this.chartInstance = new Chart(ctx, chartConfig);

    if (desiredPath) {
      this.addDesiredPath(desiredPath);
    }

    this.chartInstance.update();
  }

  /**
   * Adds desired temperature path to the chart
   * @param {Array|Object} desiredPath - Desired temperature data
   */
  addDesiredPath(desiredPath) {
    if (!Array.isArray(desiredPath) || desiredPath.length === 1) {
      const desiredTemp = Array.isArray(desiredPath) ? desiredPath[0].y : desiredPath.y;
      this.chartInstance.options.plugins.annotation = {
        annotations: {
          desiredLine: {
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
          }
        }
      };
    } else {
      this.chartInstance.data.datasets.push({
        label: 'Desired Graph',
        data: desiredPath.map(point => ({ x: point.x, y: point.y })),
        borderColor: 'red',
        borderWidth: 2,
        fill: false,
        pointRadius: 1
      });
    }
  }

  /**
   * Adds or updates a vertical line to mark the start time
   * @param {number} elapsedSeconds - Elapsed time in seconds
   */
  updateStartTimeLine(elapsedSeconds) {
    if (!this.chartInstance) return;

    // If start time line doesn't exist, create it
    if (!this.startTimeLineConfig) {
      this.startTimeLineConfig = {
        type: 'line',
        xMin: elapsedSeconds,
        xMax: elapsedSeconds,
        borderColor: 'green',
        borderWidth: 2,
        display: this.isStartTimeLineVisible,
        label: {
          content: 'Start Time',
          enabled: true,
          position: 'start'
        }
      };
      this.chartInstance.options.plugins.annotation.annotations.startTimeLine = this.startTimeLineConfig;
    }
    // Otherwise, update its position
    else {
      this.startTimeLineConfig.xMin = elapsedSeconds;
      this.startTimeLineConfig.xMax = elapsedSeconds;
    }

    this.chartInstance.update();
  }

  /**
   * Clears all sensor data from the chart while preserving the desired path
   */
  clearChartData() {
    if (this.chartInstance) {
      // Keep only the 'Desired Graph' dataset if it exists
      this.chartInstance.data.datasets = this.chartInstance.data.datasets.filter(
        dataset => dataset.label === 'Desired Graph'
      );

      // Remove start time line
      if (this.startTimeLineConfig) {
        delete this.chartInstance.options.plugins.annotation.annotations.startTimeLine;
        this.startTimeLineConfig = null;
      }

      this.chartInstance.update();
    }
  }

  /**
   * Updates the chart's time axis based on the current start time
   * @param {number} startTime - The timestamp when recording started
   */
  updateChartTimeAxis(startTime) {
    if (this.chartInstance) {
      this.chartInstance.options.scales.x.ticks.callback = (value) => {
        const timestamp = new Date(startTime + value * 1000);
        return formatTime(timestamp);
      };
      this.chartInstance.update();
    }
  }

  /**
   * Updates the chart's x-axis range based on incoming data
   * @param {number} elapsedSeconds - Current elapsed time in seconds
   */
  updateChartXAxisRange(elapsedSeconds) {
    if (!this.chartInstance) return;

    // Update the max elapsed seconds if this is the highest we've seen
    if (elapsedSeconds > this.maxElapsedSeconds) {
      this.maxElapsedSeconds = elapsedSeconds;

      // If elapsed time exceeds current x-axis max, extend it with a 10-second buffer
      const currentMax = this.chartInstance.options.scales.x.max;
      if (elapsedSeconds >= currentMax) {
        this.chartInstance.options.scales.x.max = elapsedSeconds + 10; // Add 10s buffer
      }
    }

    // Ensure x-axis max is at least 5 minutes (300 seconds)
    if (this.chartInstance.options.scales.x.max < 300) {
      this.chartInstance.options.scales.x.max = 300;
    }

    this.chartInstance.update();
  }

  /**
   * Updates chart data with new sensor readings
   * @param {Object} data - Sensor data
   * @param {number} elapsedSeconds - Elapsed time in seconds
   * @param {Set} selectedSensors - Currently selected sensors
   */
  updateChartData(data, elapsedSeconds, selectedSensors) {
    // Process data for all available sensors
    Object.entries(data).forEach(([sensorName, value]) => {
      if (typeof value === 'number') {
        // Find or create dataset for this sensor
        let dataset = this.chartInstance.data.datasets.find(ds => ds.label === sensorName);

        if (!dataset) {
          dataset = {
            label: sensorName,
            data: [],
            borderColor: getRandomColor(),
            fill: false,
            pointRadius: 1,
            hidden: !selectedSensors.has(sensorName) // Hide if not selected
          };
          this.chartInstance.data.datasets.push(dataset);
        }

        dataset.data.push({
          x: elapsedSeconds,
          y: value
        });
      }
    });

    // Update start time line with current elapsed time
    this.updateStartTimeLine(elapsedSeconds);

    this.chartInstance.update();
  }

  /**
   * Updates dataset visibility based on sensor selection
   * @param {string} sensorName - Name of the sensor
   * @param {boolean} isVisible - Whether the sensor should be visible
   */
  updateDatasetVisibility(sensorName, isVisible) {
    const dataset = this.chartInstance.data.datasets.find(ds => ds.label === sensorName);
    if (dataset) {
      dataset.hidden = !isVisible;
      this.chartInstance.update();
    }
  }

  /**
   * Resets the max elapsed time counter
   */
  resetMaxElapsedTime() {
    this.maxElapsedSeconds = 0;
  }
}