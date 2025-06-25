/**
 * SensorManager handles sensor data collection and processing
 */
export default class SensorManager {
  constructor(sensorGraph) {
    this.sensorGraph = sensorGraph;
    this.eventSource = null;
    this.availableSensors = new Set();
    this.selectedSensors = new Set();
    this.currentReadings = new Map(); // Store current sensor readings
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

    // Flatten the nested sensor data structure
    const flattenedData = this.flattenSensorData(data);

    // Update current readings
    Object.entries(flattenedData).forEach(([sensorName, value]) => {
      if (typeof value === 'number') {
        this.currentReadings.set(sensorName, value);
      }
    });

    this.updateSensorList(flattenedData);
    this.updateSensorReadings(); // Update the displayed readings

    if (this.sensorGraph.chartManager.chartInstance) {
      const elapsedSeconds = (Date.now() - startTime) / 1000;
      this.sensorGraph.chartManager.updateChartData(flattenedData, elapsedSeconds, this.selectedSensors);
      this.sensorGraph.chartManager.updateChartXAxisRange(elapsedSeconds);
    }
  }

  /**
   * Flattens the nested sensor data structure into a flat object
   * @param {Object} data - The nested sensor data
   * @returns {Object} Flattened sensor data
   */
  flattenSensorData(data) {
      const flattened = {};

      // Process sensor chip data (ADS1115, DS18B20, etc.)
      Object.entries(data).forEach(([chipType, chipData]) => {
        if (chipType === 'calculation_data') {
          // Handle calculation data separately
          if (typeof chipData === 'object' && chipData !== null) {
            Object.entries(chipData).forEach(([calcName, calcValue]) => {
              // Prefix calculation data to distinguish from sensor data
              flattened[`calc_${calcName}`] = calcValue;
            });
          }
        } else if (chipType === 'DS18B20') {
          // Handle DS18B20's nested structure: chipType -> groupName -> sensorName -> value
          if (typeof chipData === 'object' && chipData !== null) {
            Object.entries(chipData).forEach(([groupName, groupData]) => {
              if (typeof groupData === 'object' && groupData !== null) {
                Object.entries(groupData).forEach(([sensorName, sensorValue]) => {
                  if (typeof sensorValue === 'number') {
                    // Combine group name and sensor name for DS18B20
                    flattened[`${groupName}_${sensorName}`] = sensorValue;
                  }
                });
              }
            });
          }
        } else if (typeof chipData === 'object' && chipData !== null) {
          // Handle other sensor data from chips (MPL3115A2, ADS1115, etc.) - flat structure
          Object.entries(chipData).forEach(([sensorName, sensorValue]) => {
            if (typeof sensorValue === 'number') {
              // Use the sensor name directly for non-DS18B20 sensors
              flattened[sensorName] = sensorValue;
            }
          });
        }
      });

      return flattened;
    }

  /**
   * Updates the sensor list UI and manages sensor selection
   * @param {Object} data - Flattened sensor data
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
   * Renders the sensor list UI with better organization
   */
  renderSensorList() {
    const sensorList = document.getElementById('sensorList');
    sensorList.innerHTML = '';

    // Separate sensors by type for better organization
    const sensorsByType = this.categorizeSensors();

    Object.entries(sensorsByType).forEach(([category, sensors]) => {
      if (sensors.length > 0) {
        // Create category header
        const categoryHeader = document.createElement('div');
        categoryHeader.className = 'sensor-category-header';
        categoryHeader.textContent = category;
        categoryHeader.style.fontWeight = 'bold';
        categoryHeader.style.marginTop = '10px';
        categoryHeader.style.marginBottom = '5px';
        sensorList.appendChild(categoryHeader);

        // Add sensors in this category
        sensors.forEach(sensorName => {
          const div = document.createElement('div');
          div.className = 'sensor-checkbox';
          div.style.marginLeft = '15px';
          div.style.display = 'flex';
          div.style.justifyContent = 'space-between';
          div.style.alignItems = 'center';
          div.style.padding = '2px 0';

          const leftContainer = document.createElement('div');
          leftContainer.style.display = 'flex';
          leftContainer.style.alignItems = 'center';

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
          label.style.marginLeft = '5px';
          label.style.cursor = 'pointer';

          const readingSpan = document.createElement('span');
          readingSpan.className = 'sensor-reading';
          readingSpan.id = `reading-${sensorName}`;
          readingSpan.style.fontWeight = 'bold';
          readingSpan.style.color = '#0066cc';
          readingSpan.textContent = this.formatSensorReading(sensorName);

          leftContainer.appendChild(checkbox);
          leftContainer.appendChild(label);
          div.appendChild(leftContainer);
          div.appendChild(readingSpan);
          sensorList.appendChild(div);
        });
      }
    });
  }

  /**
   * Categorizes sensors by type for better UI organization
   * @returns {Object} Sensors grouped by category
   */
  categorizeSensors() {
    const categories = {
      'Temperature Sensors': [],
      'Current Sensors': [],
      'Calculations': [],
      'Other': []
    };

    Array.from(this.availableSensors).sort().forEach(sensorName => {
      const lowerName = sensorName.toLowerCase();

      if (lowerName.includes('temp') || lowerName.includes('inside') || lowerName.includes('outside')) {
        categories['Temperature Sensors'].push(sensorName);
      } else if (lowerName.includes('current')) {
        categories['Current Sensors'].push(sensorName);
      } else if (lowerName.startsWith('calc_')) {
        categories['Calculations'].push(sensorName);
      } else {
        categories['Other'].push(sensorName);
      }
    });

    return categories;
  }

  /**
   * Formats sensor reading with appropriate unit and precision
   * @param {string} sensorName - The sensor name
   * @returns {string} Formatted reading with unit
   */
  formatSensorReading(sensorName) {
    const reading = this.currentReadings.get(sensorName);
    if (reading === undefined) {
      return '-- --';
    }

    const lowerName = sensorName.toLowerCase();
    let unit = '';
    let roundedValue = Math.round(reading * 100) / 100; // Round to 0.01

    // Determine unit based on sensor type
    if (lowerName.includes('temp') || lowerName.includes('inside') || lowerName.includes('outside')) {
      unit = '°C';
    } else if (lowerName.includes('current')) {
      unit = 'A';
    } else if (lowerName.includes('pressure')) {
      unit = 'Pa';
    } else if (lowerName.includes('humidity')) {
      unit = '%';
    } else if (lowerName.includes('voltage')) {
      unit = 'V';
    } else {
      unit = ''; // No unit for calculations or unknown sensors
    }

    return `${roundedValue.toFixed(2)} ${unit}`.trim();
  }

  /**
   * Updates the displayed sensor readings
   */
  updateSensorReadings() {
    this.currentReadings.forEach((reading, sensorName) => {
      const readingElement = document.getElementById(`reading-${sensorName}`);
      if (readingElement) {
        readingElement.textContent = this.formatSensorReading(sensorName);
      }
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