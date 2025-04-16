/**
 * Utility functions for the sensor graph application
 */

/**
 * Formats a timestamp in HH:mm:ss format
 * @param {Date} date - The date to format
 * @returns {string} Formatted time string
 */
export function formatTime(date) {
  return date.toTimeString().split(' ')[0];
}

/**
 * Generates a random color for chart lines
 * @returns {string} Random color in rgb format
 */
export function getRandomColor() {
  const r = Math.floor(Math.random() * 200);
  const g = Math.floor(Math.random() * 200);
  const b = Math.floor(Math.random() * 200);
  return `rgb(${r}, ${g}, ${b})`;
}