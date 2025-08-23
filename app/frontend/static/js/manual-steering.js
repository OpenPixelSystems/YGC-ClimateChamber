import EventManager from './event-manager.js';
import ChartManager from './chart-manager.js';
import SensorManager from './sensor-manager.js';
import { formatTime } from './utils.js';

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
        
        // Automatically start sensor stream for manual control
        this.toggleSensorStream();
      }
      
      this.eventManager.setupEventListeners();
      this.setupSliders();
      this.setupPeltierCheckbox();
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
      this.eventManager.addNavigationEventListeners();
      
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
   * Setup sliders with event listeners
   */
  setupSliders() {
    const sliderWrappers = document.querySelectorAll('.slider-wrapper');

    sliderWrappers.forEach(wrapper => {
      const slider = wrapper.querySelector('.slider');
      const valueDisplay = wrapper.querySelector('.slider-value');
      const sliderType = wrapper.dataset.sliderType;

      // Update displayed value when slider moves (visual feedback only)
      slider.addEventListener('input', () => {
        valueDisplay.textContent = slider.value;
      });

      // Send data only when slider is released
      slider.addEventListener('change', () => {
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
        const response = await fetch('/start-cycle', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ originPage: 'manual-control' })
        });
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