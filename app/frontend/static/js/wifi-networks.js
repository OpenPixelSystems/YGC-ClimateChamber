/**
 * WiFi Networks Management JavaScript
 * Handles scanning, displaying, and connecting to WiFi networks
 */

let selectedNetwork = null;

/**
 * Initialize the WiFi networks page
 */
document.addEventListener('DOMContentLoaded', function() {
    loadCurrentConnection();
    scanNetworks();
});

/**
 * Load current WiFi connection status
 */
async function loadCurrentConnection() {
    try {
        const response = await fetch('/api/wifi/current');
        const data = await response.json();
        
        const currentConnectionDiv = document.getElementById('currentConnection');
        
        if (data.success) {
            if (data.current) {
                currentConnectionDiv.innerHTML = `
                    <span class="network-name">${data.current}</span>
                    <span class="connection-status connected">Connected</span>
                `;
            } else {
                currentConnectionDiv.innerHTML = `
                    <span class="connection-status disconnected">Not connected</span>
                `;
            }
        } else {
            currentConnectionDiv.innerHTML = `
                <span class="connection-status disconnected">Unable to determine connection status</span>
            `;
        }
    } catch (error) {
        console.error('Error loading connection status:', error);
        document.getElementById('currentConnection').innerHTML = `
            <span class="connection-status disconnected">Error loading connection status</span>
        `;
    }
}

/**
 * Scan for available WiFi networks
 */
async function scanNetworks() {
    const refreshBtn = document.getElementById('refreshBtn');
    const networksList = document.getElementById('networksList');
    
    // Show loading state
    refreshBtn.classList.add('refreshing');
    networksList.innerHTML = `
        <div class="loading-indicator">
            <span class="loading">Scanning for networks</span>
        </div>
    `;
    
    try {
        const response = await fetch('/api/wifi/scan');
        const data = await response.json();
        
        if (data.success) {
            displayNetworks(data.networks);
        } else {
            networksList.innerHTML = `
                <div class="loading-indicator">
                    <span style="color: var(--error-color);">Scan failed: ${data.error}</span>
                    <br><br>
                    <button class="btn btn-primary" onclick="scanNetworks()">Try Again</button>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error scanning networks:', error);
        networksList.innerHTML = `
            <div class="loading-indicator">
                <span style="color: var(--error-color);">Network error occurred</span>
                <br><br>
                <button class="btn btn-primary" onclick="scanNetworks()">Try Again</button>
            </div>
        `;
    } finally {
        refreshBtn.classList.remove('refreshing');
    }
}

/**
 * Display the list of available networks
 */
function displayNetworks(networks) {
    const networksList = document.getElementById('networksList');
    
    if (networks.length === 0) {
        networksList.innerHTML = `
            <div class="loading-indicator">
                <span>No networks found</span>
                <br><br>
                <button class="btn btn-primary" onclick="scanNetworks()">Refresh</button>
            </div>
        `;
        return;
    }
    
    networksList.innerHTML = '';
    
    networks.forEach(network => {
        const networkItem = document.createElement('div');
        networkItem.className = 'network-item';
        
        // Create signal strength bars
        const signalBars = createSignalBars(network.signal);
        
        // Security icon
        const securityIcon = network.secured ? '🔒' : '🔓';
        
        networkItem.innerHTML = `
            <div class="network-info">
                <div class="network-name">${escapeHtml(network.ssid)}</div>
                <div class="network-security">
                    <span class="security-icon">${securityIcon}</span>
                    <span>${network.secured ? 'Secured' : 'Open'}</span>
                </div>
            </div>
            <div class="signal-strength">
                <span>${network.signal}%</span>
                ${signalBars}
            </div>
            <div class="network-actions">
                <button class="btn btn-primary" data-ssid="${escapeHtml(network.ssid)}" data-secured="${network.secured}">
                    Connect
                </button>
            </div>
        `;
        
        // Add event listener to the connect button
        const connectButton = networkItem.querySelector('.btn-primary');
        connectButton.addEventListener('click', function() {
            const ssid = this.getAttribute('data-ssid');
            const secured = this.getAttribute('data-secured') === 'true';
            
            // Validate the SSID is valid
            if (!ssid || ssid === 'null' || ssid === 'undefined') {
                showStatusMessage('Error: Invalid network name', 'error');
                return;
            }
            
            initiateConnection(ssid, secured);
        });
        
        networksList.appendChild(networkItem);
    });
}

/**
 * Create signal strength bars visual indicator
 */
function createSignalBars(signal) {
    const bars = [];
    const barCount = Math.ceil(signal / 25); // 0-25%, 26-50%, 51-75%, 76-100%
    
    for (let i = 1; i <= 4; i++) {
        const activeClass = i <= barCount ? 'active' : '';
        bars.push(`<div class="signal-bar ${activeClass}"></div>`);
    }
    
    return `<div class="signal-bars">${bars.join('')}</div>`;
}

/**
 * Initiate connection to a network
 */
function initiateConnection(ssid, secured) {
    selectedNetwork = ssid;
    
    if (secured) {
        // Show password modal for secured networks
        showPasswordModal(ssid);
    } else {
        // Connect directly to open networks
        connectWithCredentials(ssid, null);
    }
}

/**
 * Show password input modal
 */
function showPasswordModal(ssid) {
    const modal = document.getElementById('passwordModal');
    const networkNameSpan = document.getElementById('modalNetworkName');
    const passwordInput = document.getElementById('networkPassword');
    
    networkNameSpan.textContent = ssid;
    passwordInput.value = '';
    passwordInput.type = 'password';
    document.getElementById('showPassword').checked = false;
    
    modal.style.display = 'flex';
    passwordInput.focus();
    
    // Handle Enter key in password field
    passwordInput.onkeypress = function(e) {
        if (e.key === 'Enter') {
            connectToNetwork();
        }
    };
}

/**
 * Close password modal
 */
function closePasswordModal() {
    const modal = document.getElementById('passwordModal');
    modal.style.display = 'none';
    selectedNetwork = null;
}

/**
 * Toggle password visibility
 */
function togglePasswordVisibility() {
    const passwordInput = document.getElementById('networkPassword');
    const showCheckbox = document.getElementById('showPassword');
    
    passwordInput.type = showCheckbox.checked ? 'text' : 'password';
}

/**
 * Connect to selected network from modal
 */
function connectToNetwork() {
    const password = document.getElementById('networkPassword').value;
    
    if (!selectedNetwork) {
        showStatusMessage('No network selected', 'error');
        return;
    }
    
    // Store selectedNetwork before closing modal (which sets it to null)
    const networkToConnect = selectedNetwork;
    closePasswordModal();
    connectWithCredentials(networkToConnect, password);
}

/**
 * Connect to network with credentials
 */
async function connectWithCredentials(ssid, password) {
    // Validate inputs on frontend
    if (!ssid || typeof ssid !== 'string' || ssid.trim() === '') {
        showStatusMessage('Invalid network name', 'error');
        return;
    }
    
    showStatusMessage(`Connecting to ${ssid}...`, 'info');
    
    try {
        const response = await fetch('/api/wifi/connect', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                ssid: ssid,
                password: password
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showStatusMessage(data.message, 'success');
            // Refresh current connection status
            setTimeout(() => {
                loadCurrentConnection();
            }, 2000);
        } else {
            showStatusMessage(data.error || 'Connection failed', 'error');
        }
    } catch (error) {
        console.error('Error connecting to network:', error);
        showStatusMessage('Network error occurred', 'error');
    }
}

/**
 * Show status message
 */
function showStatusMessage(message, type = 'info') {
    const messagesContainer = document.getElementById('statusMessages');
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `status-message ${type}`;
    messageDiv.textContent = message;
    
    messagesContainer.appendChild(messageDiv);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (messageDiv.parentNode) {
            messageDiv.parentNode.removeChild(messageDiv);
        }
    }, 5000);
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

/**
 * Close modal when clicking outside
 */
window.onclick = function(event) {
    const modal = document.getElementById('passwordModal');
    if (event.target === modal) {
        closePasswordModal();
    }
}