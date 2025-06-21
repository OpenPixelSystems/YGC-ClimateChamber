import EventManager from './event-manager.js';
import ChartManager from './chart-manager.js';
import SensorManager from './sensor-manager.js';
import { formatTime } from './utils.js';

document.querySelector('.vertical-form').addEventListener('submit', function(event) {
  event.preventDefault();
});


/**
 * SensorGraph class coordinates the different managers to handle sensor data visualization
 */
class SensorGraph {
  constructor() {
    this.startTime = null;
    this.isCycleRunning = false;

    // Initialize managers
    this.chartManager = new ChartManager(this);
    this.sensorManager = new SensorManager(this);
    this.eventManager = new EventManager(this);

    // Setup Peltier checkbox
    this.setupPeltierCheckbox();

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
    } catch (error) {
      console.error('Initialization failed:', error);
    }
  }

  /**
   * Setup Peltier checkbox with event listener
   */
  setupPeltierCheckbox() {
    const peltierCheckbox = document.getElementById('peltierCheckbox');

    peltierCheckbox.addEventListener('change', () => {
      this.updatePeltierState(peltierCheckbox.checked);
    });
  }

  /**
   * Updates Peltier elements state based on checkbox
   * @param {boolean} enabled - Whether Peltier elements should be enabled
   */
  updatePeltierState(enabled) {
    // Send Peltier state to server
    fetch('/enable_peltier', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ enabled: enabled })
    })
        .then(response => {
          if (!response.ok) {
            throw new Error('Failed to update Peltier state');
          }
          console.log(`Peltier elements ${enabled ? 'enabled' : 'disabled'}`);
        })
        .catch(error => {
          console.error('Error updating Peltier state:', error);
          // Revert checkbox state on error
          document.getElementById('peltierCheckbox').checked = !enabled;
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
    // Get custom cycle name if it exists
    const cycleName = document.getElementById('cycleName')?.value || null;

    const response = await fetch('/start-cycle', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ cycleName: cycleName })
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const result = await response.json();
    console.log("Cycle started:", result);

    this.chartManager.clearChartData();
    this.isCycleRunning = true;
    cycleButton.textContent = 'Stop Cycle';
    this.initializeStream();
    this.eventManager.addNavigationEventListeners();
  } catch (error) {
    console.error("Error starting sensor stream:", error);
    this.isCycleRunning = false;
    cycleButton.textContent = 'Start Cycle';
  }
    } else {
      this.sensorManager.closeEventSource();

      try {
        const response = await fetch('/stop-cycle', { method: 'POST' });
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
        console.error("Error stopping cycle:", error);
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