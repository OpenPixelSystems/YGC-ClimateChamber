import EventManager from './event-manager.js';
import ChartManager from './chart-manager.js';
import SensorManager from './sensor-manager.js';
import UniversalChartManager from './universal-chart-manager.js';
import { PerformanceProfiles, getOptimalProfile } from './chart-performance-config.js';
import { formatTime } from './utils.js';

/**
 * FlowChartManager - Specialized chart manager for flow execution
 */
class FlowChartManager {
  constructor(flowExecutionManager, performanceProfile = null) {
    this.flowExecutionManager = flowExecutionManager;

    // Use high-performance profile for long-running flow executions
    const profile = performanceProfile || PerformanceProfiles.HIGH_PERFORMANCE;

    this.universalManager = new UniversalChartManager({
      canvasId: 'flowGraph',
      type: 'realtime',
      ...profile
    });
  }

  /**
   * Renders the graph with initial data
   * @param {Object} response - Initial graph data
   */
  renderGraph(response) {
    const { desired_path: desiredPath, data: graphData, config, scaling } = response;

    // Apply dynamic scaling if provided
    if (scaling && (scaling.xMax !== undefined || scaling.yMax !== undefined || scaling.yMin !== undefined)) {
      this.universalManager.config.xMax = scaling.xMax;
      this.universalManager.config.yMax = scaling.yMax;
      this.universalManager.config.yMin = scaling.yMin;
    }

    // Initialize the chart
    this.universalManager.init();

    // Set start time
    if (this.flowExecutionManager.startTime) {
      this.universalManager.setStartTime(this.flowExecutionManager.startTime);
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
   * Updates the chart's x-axis range based on incoming data
   * @param {number} elapsedSeconds - Current elapsed time in seconds
   */
  updateChartXAxisRange(elapsedSeconds) {
    this.universalManager.updateTimeAxis(elapsedSeconds);
  }

  /**
   * Get the underlying chart instance
   */
  get chartInstance() {
    return this.universalManager.getChart();
  }

  /**
   * Clears all sensor data from the chart while preserving the desired path
   */
  clearChartData() {
    this.universalManager.clearData();
  }

  /**
   * Adds desired temperature path to the chart
   * @param {Array|Object} desiredPath - Desired temperature data
   */
  addDesiredPath(desiredPath) {
    this.universalManager.addDesiredPath(desiredPath);
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

/**
 * FlowSensorManager - Specialized sensor manager for flow execution
 * Extends SensorManager but doesn't render sensor checkboxes
 */
class FlowSensorManager extends SensorManager {
  constructor(flowExecutionManager) {
    super(flowExecutionManager);
    this.flowExecutionManager = flowExecutionManager;
  }

  /**
   * Override renderSensorList to do nothing since flow execution doesn't have sensor checkboxes
   */
  renderSensorList() {
    // Do nothing - flow execution doesn't have a sensor list UI
    // All sensors are automatically selected for chart display
    return;
  }

  /**
   * Override to ensure all sensors are selected for chart display
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

    // Add new sensors and automatically select them
    currentSensors.forEach(sensor => {
      if (!this.availableSensors.has(sensor)) {
        this.availableSensors.add(sensor);
        this.selectedSensors.add(sensor);
      }
    });

    // No need to call renderSensorList since we don't have that UI
  }

  /**
   * Handle sensor data specifically for flow execution
   */
  handleSensorData(data, startTime) {
    // Call parent method but skip the chart update since we handle it differently
    if (data.status === 'stopped') {
      this.closeEventSource();
      this.flowExecutionManager.chartManager.clearChartData();
      return;
    }

    // Extract guarding information
    const guardingInfo = data.guarding_info || {
      is_guarding: false,
      reasons: [],
      last_violation_time: null,
      stop_steering_temperature: false,
      stop_steering_current: false
    };

    // Flatten the nested sensor data structure and extract data sources
    const { flattenedData, dataSources } = this.flattenSensorData(data);

    // Update current readings and data sources
    Object.entries(flattenedData).forEach(([sensorName, value]) => {
      if (typeof value === 'number') {
        this.currentReadings.set(sensorName, value);

        // Determine data source
        let dataSource = dataSources[sensorName] || 'unknown';
        const cacheInfo = data._cache_info;
        if (cacheInfo && (dataSource === 'real' || dataSource === 'unknown')) {
          dataSource = cacheInfo.source;
        }
        this.dataSources.set(sensorName, dataSource);
      }
    });

    this.updateSensorList(flattenedData);

    // Update chart through flow execution manager
    this.flowExecutionManager.handleSensorData(data, startTime);
  }
}

/**
 * FlowExecutionManager coordinates flow execution with real-time data visualization
 */
class FlowExecutionManager {
  constructor() {
    this.startTime = null;
    this.isExecuting = false;
    this.flowData = null;
    this.currentStatus = null;

    // Initialize managers (reusing from manual control)
    this.chartManager = new FlowChartManager(this);
    this.sensorManager = new FlowSensorManager(this);
    this.eventManager = new EventManager(this);

    // Flow-specific properties
    this.statusUpdateInterval = null;

    // Initialize when DOM is ready
    document.addEventListener('DOMContentLoaded', () => this.initialize());
  }

  /**
   * Initialize the flow execution interface
   */
  async initialize() {
    try {
      // First check if there's an active flow execution cycle with data
      const activeCycleResponse = await fetch('/get-active-cycle-data');
      const activeCycleData = await activeCycleResponse.json();

      if (activeCycleData.active_cycle && activeCycleData.origin_page === 'flow-execution') {
        // Load existing cycle data and continue streaming
        await this.loadActiveCycleData(activeCycleData);
      } else {
        // Load flow execution data normally
        await this.loadFlowData();

        // Setup chart with stored graph configuration
        await this.setupChart();
      }

      // Setup event listeners
      this.setupEventListeners();

      // Start status monitoring
      this.startStatusMonitoring();

    } catch (error) {
      console.error('Flow execution initialization failed:', error);
      this.showError('Failed to initialize flow execution interface');
    }
  }

  /**
   * Load data from an active flow execution cycle and set up for continued streaming
   */
  async loadActiveCycleData(activeCycleData) {
    try {
      // Load flow execution data first
      await this.loadFlowData();

      // Get the stored graph configuration
      const graphResponse = await fetch('/get-stored-graph-data');
      const graphData = await graphResponse.json();

      // Set execution as running and update UI
      this.isExecuting = true;

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

      console.log(`Loaded active flow execution cycle: ${activeCycleData.cycle_name}`);
    } catch (error) {
      console.error('Error loading active flow execution cycle data:', error);
    }
  }

  /**
   * Load flow execution data from server
   */
  async loadFlowData() {
    try {
      const response = await fetch('/get-execution-flow');
      const data = await response.json();

      if (data.success) {
        this.flowData = data.executionFlow;
        this.currentStatus = data.status;
        this.updateUI();
      } else {
        throw new Error(data.error || 'Failed to load flow data');
      }
    } catch (error) {
      console.error('Failed to load flow data:', error);
      throw error;
    }
  }

  /**
   * Setup chart with graph configuration
   */
  async setupChart() {
    try {
      // Get stored graph configuration
      const response = await fetch('/get-stored-graph-data');
      const graphData = await response.json();

      // Render chart
      this.chartManager.renderGraph(graphData);

    } catch (error) {
      console.error('Failed to setup chart:', error);
      // Continue without chart if it fails
    }
  }

  /**
   * Setup event listeners for control buttons
   */
  setupEventListeners() {
    // Control buttons
    document.getElementById('startFlowBtn')?.addEventListener('click', () => this.startExecution());
    document.getElementById('pauseFlowBtn')?.addEventListener('click', () => this.pauseExecution());
    document.getElementById('stopFlowBtn')?.addEventListener('click', () => this.stopExecution());
    document.getElementById('resetFlowBtn')?.addEventListener('click', () => this.resetExecution());
  }

  /**
   * Start monitoring execution status
   */
  startStatusMonitoring() {
    this.statusUpdateInterval = setInterval(() => {
      this.updateExecutionStatus();
    }, 2000); // Update every 2 seconds
  }

  /**
   * Stop status monitoring
   */
  stopStatusMonitoring() {
    if (this.statusUpdateInterval) {
      clearInterval(this.statusUpdateInterval);
      this.statusUpdateInterval = null;
    }
  }

  /**
   * Update execution status from server
   */
  async updateExecutionStatus() {
    try {
      const response = await fetch('/get-flow-execution-status');
      const data = await response.json();

      if (data.success) {
        this.currentStatus = data.status;
        this.updateStatusDisplay();
        this.updateStepProgress();
      }
    } catch (error) {
      console.error('Failed to update execution status:', error);
    }
  }

  /**
   * Update the UI with flow data
   */
  updateUI() {
    if (!this.flowData) return;

    // Update flow info
    document.getElementById('flowId').textContent = this.flowData.flowId || 'Unknown';

    // Populate flow steps
    this.populateFlowSteps();

    // Update initial status
    this.updateStatusDisplay();
  }

  /**
   * Populate the flow steps overview
   */
  populateFlowSteps() {
    const stepsContainer = document.getElementById('stepsContainer');
    if (!stepsContainer || !this.flowData?.executionSteps) return;

    stepsContainer.innerHTML = '';

    this.flowData.executionSteps.forEach((step, index) => {
      const stepElement = document.createElement('div');
      stepElement.className = 'step-item';
      stepElement.dataset.stepIndex = index;

      stepElement.innerHTML = `
        <div class="step-item-number">${step.stepId}</div>
        <div class="step-item-content">
          <div class="step-item-title">${step.stepType.replace(/-/g, ' ')}</div>
          <div class="step-item-desc">${step.description}</div>
        </div>
      `;

      stepsContainer.appendChild(stepElement);
    });
  }

  /**
   * Update status display
   */
  updateStatusDisplay() {
    if (!this.currentStatus) return;

    // Update status text
    const statusElement = document.getElementById('executionStatus');
    if (statusElement) {
      statusElement.textContent = this.currentStatus.isExecuting ? 'Running' : 'Ready';
      statusElement.className = `status-value ${this.currentStatus.isExecuting ? 'status-running' : 'status-ready'}`;
    }

    // Update progress
    const progressText = document.getElementById('progressText');
    const progressFill = document.getElementById('progressFill');

    if (progressText && progressFill) {
      const progress = Math.round(this.currentStatus.progressPercentage || 0);
      progressText.textContent = `${progress}%`;
      progressFill.style.width = `${progress}%`;
    }

    // Update current step info
    this.updateCurrentStepDisplay();

    // Update button states
    this.updateButtonStates();
  }

  /**
   * Update current step display
   */
  updateCurrentStepDisplay() {
    if (!this.currentStatus?.currentStep) return;

    const step = this.currentStatus.currentStep;

    document.getElementById('stepNumber').textContent = step.stepId || '--';
    document.getElementById('stepType').textContent = step.stepType?.replace(/-/g, ' ') || '--';
    document.getElementById('stepDescription').textContent = step.description || 'No description';

    // Update step details with special handling for start nodes
    if (step.stepType === 'start-node') {
      document.getElementById('targetTemperature').textContent = 'Read Current';
      document.getElementById('tolerance').textContent = 'N/A';
      document.getElementById('duration').textContent = 'Instant';
    } else {
      // Handle target temperature display
      let tempText = '--';
      if (step.targetTemperature !== null) {
        tempText = `${step.targetTemperature}°C`;
      } else if (step.readCurrentTemperature && this.currentStatus?.initialTemperature !== null) {
        // For hold nodes that read current temp, show the initial temperature from start node
        tempText = `${this.currentStatus.initialTemperature.toFixed(1)}°C (from start)`;
      } else if (step.readCurrentTemperature) {
        tempText = 'Current temp (reading...)';
      }

      document.getElementById('targetTemperature').textContent = tempText;
      document.getElementById('tolerance').textContent =
        step.tolerance ? `±${step.tolerance}°C` : '--';
      document.getElementById('duration').textContent =
        step.duration ? `${step.duration} min` : '--';
    }
  }

  /**
   * Update step progress highlighting
   */
  updateStepProgress() {
    const stepItems = document.querySelectorAll('.step-item');
    const currentIndex = this.currentStatus?.currentStepIndex || 0;
    const isExecuting = this.currentStatus?.isExecuting;
    const currentStep = this.currentStatus?.currentStep;

    stepItems.forEach((item, index) => {
      item.classList.remove('active', 'completed');

      if (index < currentIndex) {
        item.classList.add('completed');
      } else if (index === currentIndex) {
        // If on end node and not executing anymore, mark as completed
        if (currentStep?.stepType === 'end-node' && !isExecuting) {
          item.classList.add('completed');
        } else if (isExecuting) {
          item.classList.add('active');
        }
      }
    });
  }

  /**
   * Update button states based on execution status
   */
  updateButtonStates() {
    const startBtn = document.getElementById('startFlowBtn');
    const pauseBtn = document.getElementById('pauseFlowBtn');
    const stopBtn = document.getElementById('stopFlowBtn');
    const resetBtn = document.getElementById('resetFlowBtn');

    const isExecuting = this.currentStatus?.isExecuting || false;

    if (startBtn) startBtn.style.display = isExecuting ? 'none' : 'block';
    if (pauseBtn) pauseBtn.style.display = isExecuting ? 'block' : 'none';
    if (stopBtn) stopBtn.style.display = isExecuting ? 'block' : 'none';
    if (resetBtn) resetBtn.style.display = isExecuting ? 'none' : 'block';
  }

  /**
   * Start flow execution
   */
  async startExecution() {
    try {
      const response = await fetch('/start-flow-execution', { method: 'POST' });
      const data = await response.json();

      if (data.success) {
        this.isExecuting = true;
        this.startTime = Date.now();

        // Ensure chart is initialized
        if (!this.chartManager.chartInstance) {
          try {
            // Try to initialize with basic config if setupChart failed
            this.chartManager.universalManager.init();
          } catch (error) {
            console.error('Failed to initialize chart:', error);
          }
        }

        // Start sensor streaming
        this.sensorManager.createEventSource(this.startTime);

        // Update chart time axis
        this.chartManager.updateChartTimeAxis(this.startTime);

        this.showSuccess('Flow execution started');
      } else {
        this.showError(data.error || 'Failed to start flow execution');
      }
    } catch (error) {
      console.error('Failed to start execution:', error);
      this.showError('Failed to start flow execution');
    }
  }

  /**
   * Pause flow execution
   */
  async pauseExecution() {
    // Note: This would require implementation in the backend
    this.showInfo('Pause functionality not yet implemented');
  }

  /**
   * Stop flow execution
   */
  async stopExecution() {
    try {
      const response = await fetch('/stop-flow-execution', { method: 'POST' });
      const data = await response.json();

      if (data.success) {
        this.isExecuting = false;

        // Stop sensor streaming
        this.sensorManager.closeEventSource();

        this.showSuccess('Flow execution stopped');
      } else {
        this.showError(data.error || 'Failed to stop flow execution');
      }
    } catch (error) {
      console.error('Failed to stop execution:', error);
      this.showError('Failed to stop flow execution');
    }
  }

  /**
   * Reset flow execution
   */
  async resetExecution() {
    if (confirm('Are you sure you want to reset the flow? This will clear all progress.')) {
      // Note: This would require implementation in the backend
      this.showInfo('Reset functionality not yet implemented');
    }
  }

  /**
   * Handle sensor data updates (called by sensor manager)
   */
  handleSensorData(data, startTime) {
    // Update sensor readings display
    this.updateSensorReadings(data);

    // Update chart with proper method - use flattened data
    if (this.chartManager && this.chartManager.chartInstance) {
      const elapsedSeconds = (Date.now() - startTime) / 1000;
      const { flattenedData } = this.sensorManager.flattenSensorData(data);

      this.chartManager.updateChartData(flattenedData, elapsedSeconds, this.sensorManager.getSelectedSensors());
      this.chartManager.updateChartXAxisRange(elapsedSeconds);
    }
  }

  /**
   * Update sensor readings display
   */
  updateSensorReadings(data) {
    const readingsContainer = document.getElementById('sensorReadings');
    if (!readingsContainer) return;

    // Use the sensor manager's flattened data and formatting
    const { flattenedData } = this.sensorManager.flattenSensorData(data);

    // Update current readings in sensor manager for formatting
    Object.entries(flattenedData).forEach(([sensorName, value]) => {
      if (typeof value === 'number') {
        this.sensorManager.currentReadings.set(sensorName, value);
      }
    });

    // Clear existing readings
    readingsContainer.innerHTML = '';

    // Add sensor readings using the same format as manual control
    Object.entries(flattenedData).forEach(([sensor, reading]) => {
      if (typeof reading === 'number') {
        const readingElement = document.createElement('div');
        readingElement.className = 'sensor-reading';

        // Format the reading using sensor manager's formatting
        const formattedReading = this.sensorManager.formatSensorReading(sensor);

        readingElement.innerHTML = `
          <span class="sensor-name">${sensor}</span>
          <span class="sensor-value">${formattedReading}</span>
        `;
        readingsContainer.appendChild(readingElement);
      }
    });
  }

  /**
   * Show success message
   */
  showSuccess(message) {
    console.log('Success:', message);
    // You could integrate with a toast notification system here
  }

  /**
   * Show error message
   */
  showError(message) {
    console.error('Error:', message);
    // You could integrate with a toast notification system here
    alert(`Error: ${message}`);
  }

  /**
   * Show info message
   */
  showInfo(message) {
    console.info('Info:', message);
    // You could integrate with a toast notification system here
    alert(`Info: ${message}`);
  }

  /**
   * Cleanup when leaving page
   */
  cleanup() {
    this.stopStatusMonitoring();
    this.sensorManager.closeEventSource();
  }
}

// Initialize flow execution manager
const flowExecutionManager = new FlowExecutionManager();

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
  flowExecutionManager.cleanup();
});

export default FlowExecutionManager;