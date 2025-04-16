/**
 * SensorManager handles sensor data collection and processing
 */
export default class SensorManager {
  constructor(sensorGraph) {
    this.sensorGraph = sensorGraph;
    this.eventSource = null;
    this.availableSensors = new Set();
    this.selectedSensors = new Set();
  }

  /**
   * Creates and sets up the EventSource for streaming sensor data
   * @param {number} startTime - The start time timestamp
   */
  createEventSource(startTime) {
    this.eventSource = new EventSource('/stream');

    this.eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleSensorData(data, startTime);
    };

    this.eventSource.onerror = (error) => {
      console.error('EventSource failed:', error);
      this.closeEventSource();
      this.sensorGraph.handleCycleStop();
    };
  }

  /**
   * Closes the event source if it exists
   */
  closeEventSource() {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }

  /**
   * Handles incoming sensor data and updates the chart
   * @param {Object} data - The sensor data
   * @param {number} startTime - The timestamp when recording started
   */
  handleSensorData(data, startTime) {
    if (data.status === 'stopped') {
      this.closeEventSource();
      this.sensorGraph.chartManager.clearChartData();
      return;
    }

    this.updateSensorList(data);

    if (this.sensorGraph.chartManager.chartInstance) {
      const elapsedSeconds = (Date.now() - startTime) / 1000;
      this.sensorGraph.chartManager.updateChartData(data, elapsedSeconds, this.selectedSensors);
      this.sensorGraph.chartManager.updateChartXAxisRange(elapsedSeconds);
    }
  }

  /**
   * Updates the sensor list UI and manages sensor selection
   * @param {Object} data - Sensor data
   */
  updateSensorList(data) {
    const currentSensors = new Set(
      Object.keys(data).filter(key => typeof data[key] === 'number')
    );

    // Remove inactive sensors
    for (const sensor of this.availableSensors) {
      if (!currentSensors.has(sensor)) {
        this.availableSensors.delete(sensor);
        this.selectedSensors.delete(sensor);
      }
    }

    // Add new sensors
    currentSensors.forEach(sensor => {
      if (!this.availableSensors.has(sensor)) {
        this.availableSensors.add(sensor);
        this.selectedSensors.add(sensor);
      }
    });

    this.renderSensorList();
  }

  /**
   * Renders the sensor list UI
   */
  renderSensorList() {
    const sensorList = document.getElementById('sensorList');
    sensorList.innerHTML = '';

    Array.from(this.availableSensors).sort().forEach(sensorName => {
      const div = document.createElement('div');
      div.className = 'sensor-checkbox';

      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.id = sensorName;
      checkbox.checked = this.selectedSensors.has(sensorName);
      checkbox.addEventListener('change', (e) => {
        if (e.target.checked) {
          this.selectedSensors.add(sensorName);
        } else {
          this.selectedSensors.delete(sensorName);
        }
        // Update dataset visibility
        this.sensorGraph.chartManager.updateDatasetVisibility(sensorName, e.target.checked);
      });

      const label = document.createElement('label');
      label.htmlFor = sensorName;
      label.textContent = sensorName;

      div.appendChild(checkbox);
      div.appendChild(label);
      sensorList.appendChild(div);
    });
  }

  /**
   * Gets the current set of selected sensors
   * @returns {Set} The selected sensors
   */
  getSelectedSensors() {
    return this.selectedSensors;
  }
}