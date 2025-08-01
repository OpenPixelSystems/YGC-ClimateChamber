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
 * Navigate to settings page
 */
function navigateToSettings() {
    window.location.href = '/edit-config';
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
 * Fetch and update storage information
 */
async function updateStorageInfo() {
    try {
        const response = await fetch('/api/storage-info');
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                const storage = data.storage;
                const storagePercent = storage.usage_percent;
                
                // Update the progress bar
                const storageFill = document.getElementById('storageFill');
                const storageText = document.getElementById('storageText');
                const storageIndicator = document.getElementById('storageIndicator');
                
                if (storageFill && storageText && storageIndicator) {
                    // Update the fill width
                    storageFill.style.width = `${storagePercent}%`;
                    
                    // Update the text to show percentage
                    storageText.textContent = `${storagePercent}%`;
                    
                    // Remove previous color classes
                    storageFill.classList.remove('warning', 'danger');
                    
                    // Apply color based on usage level
                    if (storagePercent >= 90) {
                        storageFill.classList.add('danger');
                    } else if (storagePercent >= 75) {
                        storageFill.classList.add('warning');
                    }
                    
                    // Update tooltip with detailed information
                    storageIndicator.title = `Storage Usage: ${storagePercent}%\nUsed: ${storage.used_gb} GB\nFree: ${storage.free_gb} GB\nTotal: ${storage.total_gb} GB`;
                }
            }
        } else {
            console.warn('Failed to fetch storage info:', response.status);
        }
    } catch (error) {
        console.error('Error fetching storage info:', error);
        // Show error state
        const storageText = document.getElementById('storageText');
        if (storageText) {
            storageText.textContent = 'ERR';
        }
    }
}

/**
 * Initialize base template functionality
 */
document.addEventListener('DOMContentLoaded', () => {
    initializeDarkMode();
    
    // Update storage info immediately
    updateStorageInfo();
    
    // Update storage info every 30 seconds
    setInterval(updateStorageInfo, 30000);
});