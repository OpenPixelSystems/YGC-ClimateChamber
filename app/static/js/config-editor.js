// config-editor.js
// Dynamically renders config fields and handles save for integer fields only

document.addEventListener('DOMContentLoaded', () => {
    const configFormDiv = document.getElementById('config-form');
    const saveBtn = document.getElementById('save-config-btn');
    const fileSelector = document.getElementById('filename');
    let configData = {};
    let filename = fileSelector ? fileSelector.value : null;

    // Helper to recursively render config fields
    function renderConfig(obj, path = []) {
        let html = '';
        for (const key in obj) {
            if (typeof obj[key] === 'object' && obj[key] !== null && !Array.isArray(obj[key])) {
                html += `<fieldset class="config-group"><legend>${key}</legend>${renderConfig(obj[key], path.concat(key))}</fieldset>`;
            } else if (typeof obj[key] === 'number' && Number.isInteger(obj[key])) {
                const fieldId = [...path, key].join('.');
                html += `<div class="config-field">
                    <label for="${fieldId}">${fieldId}</label>
                    <input type="number" id="${fieldId}" name="${fieldId}" value="${obj[key]}" />
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
            } else if (typeof obj[key] === 'number' && Number.isInteger(obj[key])) {
                const fieldId = [...path, key].join('.');
                const input = document.getElementById(fieldId);
                if (input) {
                    obj[key] = parseInt(input.value, 10);
                }
            }
        }
    }

    function fetchAndRenderConfig() {
        if (!filename) return;
        fetch(`/config/api/get-config?filename=${encodeURIComponent(filename)}`)
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
        fetch('/config/api/save-config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: filename, config: configData })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                alert('Configuration saved successfully!');
            } else {
                alert('Error saving config: ' + (data.error || 'Unknown error'));
            }
        });
    });

    // Reload config when file changes
    if (fileSelector) {
        fileSelector.addEventListener('change', function() {
            filename = this.value;
            fetchAndRenderConfig();
        });
    }

    fetchAndRenderConfig();
});
