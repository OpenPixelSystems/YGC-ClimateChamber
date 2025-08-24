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
   * Handler for beforeunload event to inform users the cycle will continue
   * @param {Event} e - The beforeunload event
   */
  handleBeforeUnload(e) {
    if (this.sensorGraph.isCycleRunning) {
      // Inform user that cycle will continue running in background
      const message = 'Cycle will continue running in the background. You can return to view data anytime.';
      e.returnValue = message;
      return message;
    } else {
      // If cycle is stopped and we're leaving the page, clear the graph
      // Use fetch with keepalive for navigation scenarios
      fetch('/clear-graph-if-needed', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
        keepalive: true
      }).catch(() => {
        // Fallback to sendBeacon if fetch fails
        navigator.sendBeacon('/clear-graph-if-needed', JSON.stringify({}));
      });
    }
  }

  /**
   * Cleanup function to be called when page is actually unloading
   * Only closes the event source but keeps the cycle running
   */
  cleanupOnUnload() {
    if (this.sensorGraph.isCycleRunning) {
      // Only close the EventSource, don't stop the cycle
      this.sensorGraph.sensorManager.closeEventSource();
    } else {
      // If cycle is not running and page is closing, clear the desired graph
      // This handles the case where cycle was stopped but page remained loaded
      navigator.sendBeacon('/clear-graph-if-needed', JSON.stringify({}));
    }
  }

  /**
   * Add event listeners for page navigation events
   */
  addNavigationEventListeners() {
    window.addEventListener('beforeunload', this.handleBeforeUnload);
    window.addEventListener('unload', this.cleanupOnUnload);
    window.addEventListener('pagehide', this.cleanupOnUnload);
  }

  /**
   * Remove event listeners for page navigation events
   */
  removeNavigationEventListeners() {
    window.removeEventListener('beforeunload', this.handleBeforeUnload);
    window.removeEventListener('unload', this.cleanupOnUnload);
    window.removeEventListener('pagehide', this.cleanupOnUnload);
  }

  /**
   * Wrapper for the toggleSensorStream method in the main class
   */
  toggleSensorStream() {
    this.sensorGraph.toggleSensorStream();
  }
}