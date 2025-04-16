/**
 * EventManager handles all event listeners for the application
 */
export default class EventManager {
  constructor(sensorGraph) {
    this.sensorGraph = sensorGraph;

    // Bind methods to maintain 'this' context
    this.handleBeforeUnload = this.handleBeforeUnload.bind(this);
    this.cleanupOnUnload = this.cleanupOnUnload.bind(this);
    this.toggleSensorStream = this.toggleSensorStream.bind(this);
  }

  /**
   * Set up the main event listeners
   */
  setupEventListeners() {
    const cycleButton = document.getElementById('StartCycle');
    cycleButton.addEventListener('click', this.toggleSensorStream);
  }

  /**
   * Handler for beforeunload event to warn users before leaving the page
   * @param {Event} e - The beforeunload event
   * @returns {string} Message to display in the confirmation dialog
   */
  handleBeforeUnload(e) {
    if (this.sensorGraph.isCycleRunning) {
      // Standard way to show a confirmation dialog when leaving page
      const message = 'Cycle is still running! Leaving this page will stop data collection. Are you sure you want to leave?';
      e.returnValue = message; // Standard for most browsers
      return message; // For older browsers
    }
  }

  /**
   * Cleanup function to be called when page is actually unloading
   * This sends a final request to stop sensors
   */
  cleanupOnUnload() {
    if (this.sensorGraph.isCycleRunning) {
      // Use sendBeacon which is designed specifically for analytics
      // data on page unload. It's more reliable than fetch/XHR in unload events.
      navigator.sendBeacon('/stop_cycle', JSON.stringify({}));

      // Close the EventSource if it exists
      this.sensorGraph.sensorManager.closeEventSource();
    }
  }

  /**
   * Add event listeners for page navigation events
   */
  addNavigationEventListeners() {
    window.addEventListener('beforeunload', this.handleBeforeUnload);
    window.addEventListener('unload', this.cleanupOnUnload);
  }

  /**
   * Remove event listeners for page navigation events
   */
  removeNavigationEventListeners() {
    window.removeEventListener('beforeunload', this.handleBeforeUnload);
    window.removeEventListener('unload', this.cleanupOnUnload);
  }

  /**
   * Wrapper for the toggleSensorStream method in the main class
   */
  toggleSensorStream() {
    this.sensorGraph.toggleSensorStream();
  }
}