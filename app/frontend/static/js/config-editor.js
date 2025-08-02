// config-editor.js
// Dynamically renders config fields and handles save for integer fields only

document.addEventListener('DOMContentLoaded', () => {
    const configFormDiv = document.getElementById('config-form');
    const saveBtn = document.getElementById('save-config-btn');
    const fileSelector = document.getElementById('filename');
    let configData = {};
    let filename = fileSelector ? fileSelector.value : null;
    const SENSOR_GROUPS = ["Environment", "Inside", "Peltier", "External", "System"];
    const PELTIER_DRIVERS = ["BTS7960", "TB6612FNG"]


    function renderConfig(obj, path = []) {
        let html = '';
        for (const key in obj) {
            if (key === 'editable' && typeof obj[key] === 'object' && obj[key] !== null) {
                html += '<div class="config-fields">';
                for (const subKey in obj[key]) {
                    const fieldId = [...path, key, subKey].join('.');

                    if (subKey === 'sensor_group') {
                        // Render dropdown for sensor_group
                        html += `<div class="config-field">
                            <label for="${fieldId}">${subKey}</label>
                            <select id="${fieldId}" name="${fieldId}">`;

                        for (const group of SENSOR_GROUPS) {
                            const selected = obj[key][subKey] === group ? 'selected' : '';
                            html += `<option value="${group}" ${selected}>${group}</option>`;
                        }

                        html += `</select>
                        </div>`;
                    }
                    else if (subKey === 'driver_type') {
                        // Render dropdown for peltier_types
                        html += `<div class="config-field">
                            <label for="${fieldId}">${subKey}</label>
                            <select id="${fieldId}" name="${fieldId}">`;

                        for (const group of PELTIER_DRIVERS) {
                            const selected = obj[key][subKey] === group ? 'selected' : '';
                            html += `<option value="${group}" ${selected}>${group}</option>`;
                        }

                        html += `</select>
                        </div>`;
                    }
                    else if (typeof obj[key][subKey] === 'number' && !isNaN(obj[key][subKey])) {
                        html += `<div class="config-field">
                            <label for="${fieldId}">${subKey}</label>
                            <input type="number" id="${fieldId}" name="${fieldId}" value="${obj[key][subKey]}" />
                        </div>`;
                    }
                    else if (typeof obj[key][subKey] === 'string') {
                        html += `<div class="config-field">
                            <label for="${fieldId}">${subKey}</label>
                            <input type="text" id="${fieldId}" name="${fieldId}" value="${obj[key][subKey]}" />
                        </div>`;
                    }
                }
                html += '</div>';
            } else if (typeof obj[key] === 'object' && obj[key] !== null && !Array.isArray(obj[key])) {
                html += `<div class="config-group">
                            <div class="config-header">
                                <h3>${key}</h3>
                            </div>
                            ${renderConfig(obj[key], path.concat(key))}
                        </div>`;
            }
        }
        return html;
    }

   // Helper to recursively update configData from form fields
    function updateConfigFromForm(obj, path = []) {
        for (const key in obj) {
            if (typeof obj[key] === 'object' && obj[key] !== null && !Array.isArray(obj[key])) {
                updateConfigFromForm(obj[key], path.concat(key));
            } else if (typeof obj[key] === 'number' && !isNaN(obj[key])) {
                const fieldId = [...path, key].join('.');
                const input = document.getElementById(fieldId);
                if (input) {
                    obj[key] = parseFloat(input.value);
                }
            } else if (typeof obj[key] === 'string') {
                const fieldId = [...path, key].join('.');
                const input = document.getElementById(fieldId);
                if (input) {
                    obj[key] = input.value; // For both text inputs and select dropdowns
                }
            }
        }
    }

    function fetchAndRenderConfig() {
        if (!filename) return;
        fetch(`/api/get-config?filename=${encodeURIComponent(filename)}`)
            .then(res => res.json())
            .then(data => {
                if (data.config) {
                    configData = data.config;
                    configFormDiv.innerHTML = renderConfig(configData);
                } else {
                    configFormDiv.innerHTML = `<div class="error">Failed to load config: ${data.error || 'Unknown error'}</div>`;
                }
            });
    }

    saveBtn.addEventListener('click', function(e) {
        e.preventDefault();
        updateConfigFromForm(configData);
        
        // Check if we're editing raspberry_pi_config.json
        const isRaspberryPiConfig = filename === 'raspberry_pi_config.json';
        
        fetch('/api/save-config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                filename: filename, 
                config: configData,
                skipReload: isRaspberryPiConfig  // Skip automatic reload for raspberry pi config
            })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                if (isRaspberryPiConfig) {
                    // For raspberry_pi_config, restart the entire service
                    if (confirm('Configuration saved! The service needs to restart to apply GPIO pin changes. Restart now?')) {
                        restartService();
                    }
                } else {
                    alert('Configuration saved successfully!');
                }
            } else {
                alert('Error saving config: ' + (data.error || 'Unknown error'));
            }
        });
    });
    
    // Add restart service function (reused from base.js)
    async function restartService() {
        try {
            const response = await fetch('/restart-service', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                alert('Service restart initiated. The application will be unavailable for a few moments.');
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

    // Reload config when file changes
    if (fileSelector) {
        fileSelector.addEventListener('change', function() {
            filename = this.value;
            fetchAndRenderConfig();
        });
    }

    fetchAndRenderConfig();
});
