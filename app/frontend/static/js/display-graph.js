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
      // First check if there's an active cycle with data
      const activeCycleResponse = await fetch('/get-active-cycle-data');
      const activeCycleData = await activeCycleResponse.json();
      
      if (activeCycleData.active_cycle) {
        // Load existing cycle data and continue streaming
        await this.loadActiveCycleData(activeCycleData);
      } else {
        // Load stored graph configuration only
        const response = await fetch('/get-stored-graph-data');
        const data = await response.json();
        this.startTime = Date.now();
        this.chartManager.renderGraph(data);
      }
      
      this.eventManager.setupEventListeners();
      // Always add navigation listeners for display-graph to handle graph cleanup
      this.eventManager.addNavigationEventListeners();
    } catch (error) {
      console.error('Initialization failed:', error);
    }
  }

  /**
   * Load data from an active cycle and set up for continued streaming
   */
  async loadActiveCycleData(activeCycleData) {
    try {
      // Get the stored graph configuration
      const graphResponse = await fetch('/get-stored-graph-data');
      const graphData = await graphResponse.json();
      
      // Set cycle as running and update UI
      this.isCycleRunning = true;
      const cycleButton = document.getElementById('StartCycle');
      if (cycleButton) {
        cycleButton.textContent = 'Stop Cycle';
      }
      
      // Render the graph with the configuration
      this.chartManager.renderGraph(graphData);
      
      // Load and display the existing cycle data
      if (activeCycleData.data) {
        this.chartManager.loadExistingCycleData(activeCycleData.data, activeCycleData.cycle_start_time);
      }
      
      // Set up streaming to continue from where we left off
      this.startTime = new Date(activeCycleData.cycle_start_time).getTime();
      this.chartManager.updateChartTimeAxis(this.startTime);
      this.sensorManager.createEventSource(this.startTime);
      
      console.log(`Loaded active cycle: ${activeCycleData.cycle_name}`);
    } catch (error) {
      console.error('Error loading active cycle data:', error);
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
   * Initializes the sensor data stream for new cycles
   */
  initializeStream() {
    this.sensorManager.closeEventSource();

    // Only reset start time for new cycles (not when reconnecting to active cycle)
    if (!this.startTime) {
      this.startTime = Date.now();
    }
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
      body: JSON.stringify({ cycleName: cycleName, originPage: 'display-graph' })
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