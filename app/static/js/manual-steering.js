import EventManager from './event-manager.js';
import ChartManager from './chart-manager.js';
import SensorManager from './sensor-manager.js';
import { formatTime } from './utils.js';

/**
 * SensorGraph class coordinates the different managers to handle sensor data visualization
 */
class SensorGraph {
  constructor() {
  //TODO chartinstance isn't cleared when page is loaded, resulting in desiredgraph still being visible
    this.startTime = null;
    this.isCycleRunning = false;

    // Initialize managers
    this.chartManager = new ChartManager(this);
    this.sensorManager = new SensorManager(this);
    this.eventManager = new EventManager(this);

    // Initialize when DOM is ready
    document.addEventListener('DOMContentLoaded', () => this.initialize());
  }

  /**
   * Initialize the graph and event listeners
   */
  async initialize() {
    try {
      const response = await fetch('/get-stored-graph-data');
      const data = await response.json();

      this.startTime = Date.now();
      this.chartManager.renderGraph(data);
      this.eventManager.setupEventListeners();

      // Setup sliders
      this.setupSliders();

      // Automatically start sensor stream
      this.toggleSensorStream();
    } catch (error) {
      console.error('Initialization failed:', error);
    }
  }

  /**
   * Setup sliders with event listeners
   */
  setupSliders() {
    const sliderWrappers = document.querySelectorAll('.slider-wrapper');

    sliderWrappers.forEach(wrapper => {
      const slider = wrapper.querySelector('.slider');
      const valueDisplay = wrapper.querySelector('.slider-value');
      const sliderType = wrapper.dataset.sliderType;

      // Update displayed value when slider moves
      slider.addEventListener('input', () => {
        valueDisplay.textContent = slider.value;

        // Call specific update method based on slider type
        switch(sliderType) {
          case 'power':
            this.updatePower(parseInt(slider.value));
            break;
          // Future sliders can be added here
        }
      });
    });
  }

  /**
   * Updates power based on slider value
   * @param {number} powerValue - Power value between 0 and 100
   */
  updatePower(powerValue) {
    // Send power value to server
    fetch('/update-power', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ power: powerValue })
    })
    .then(response => {
      if (!response.ok) {
        throw new Error('Failed to update power');
      }
      console.log(`Power set to ${powerValue}%`);
    })
    .catch(error => {
      console.error('Error updating power:', error);
    });
  }

  /**
   * Initializes the sensor data stream
   */
  initializeStream() {
    this.sensorManager.closeEventSource();

    this.startTime = Date.now();
    this.chartManager.resetMaxElapsedTime();
    this.chartManager.updateChartTimeAxis(this.startTime);

    this.sensorManager.createEventSource(this.startTime);
  }

  /**
   * Toggles the sensor stream between start and stop states
   */
  async toggleSensorStream() {
    const cycleButton = document.getElementById('StartCycle');

    if (!this.isCycleRunning) {
      try {
        const response = await fetch('/start_cycle', { method: 'POST' });
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const result = await response.json();
        console.log("Sensors started:", result);

        this.chartManager.clearChartData();
        this.isCycleRunning = true;
        cycleButton.textContent = 'Stop Cycle';
        this.initializeStream();
        this.eventManager.addNavigationEventListeners();
      } catch (error) {
        console.error("Error starting cycle stream:", error);
        this.isCycleRunning = false;
        cycleButton.textContent = 'Start Cycle';
      }
    } else {
      this.sensorManager.closeEventSource();

      try {
        const response = await fetch('/stop_cycle', { method: 'POST' });
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const result = await response.json();
        console.log("Cycle stopped:", result);

        this.chartManager.clearChartData();
        this.isCycleRunning = false;
        cycleButton.textContent = 'Start Cycle';
        this.eventManager.removeNavigationEventListeners();
      } catch (error) {
        console.error("Error stopping cycle stream:", error);
      }
    }
  }

  /**
   * Handles the case when cycle stops due to an error
   */
  handleCycleStop() {
    this.isCycleRunning = false;
    document.getElementById('StartCycle').textContent = 'Start Cycle';
    this.eventManager.removeNavigationEventListeners();
  }
}

// Initialize the application
export default new SensorGraph();