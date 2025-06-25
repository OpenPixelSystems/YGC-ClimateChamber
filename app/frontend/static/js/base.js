/**
 * Base Template JavaScript
 * Contains global functionality for navigation and system controls
 */

/**
 * Toggle dark mode theme
 */
function toggleDarkMode() {
    document.documentElement.classList.toggle('dark-mode');
    const isDarkMode = document.documentElement.classList.contains('dark-mode');
    localStorage.setItem('darkMode', isDarkMode);
}

/**
 * Restart the climate chamber service
 */
async function restartService() {
    if (confirm('Are you sure you want to restart the climate chamber service? This will disconnect all users temporarily.')) {
        try {
            const response = await fetch('/restart-service', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                alert('Service restart initiated. The application will be unavailable for a few moments.');
                // Optionally redirect to a loading page or show a reconnection message
                setTimeout(() => {
                    window.location.reload();
                }, 3000);
            } else {
                const error = await response.json();
                alert('Failed to restart service: ' + (error.error || 'Unknown error'));
            }
        } catch (error) {
            alert('Error communicating with server: ' + error.message);
        }
    }
}

/**
 * Initialize dark mode based on stored preference
 */
function initializeDarkMode() {
    const isDarkMode = localStorage.getItem('darkMode') === 'true';
    if (isDarkMode) {
        document.documentElement.classList.add('dark-mode');
    } else {
        document.documentElement.classList.remove('dark-mode');
    }
}

/**
 * Initialize base template functionality
 */
document.addEventListener('DOMContentLoaded', () => {
    initializeDarkMode();
});