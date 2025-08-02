class LogsViewer {
    constructor() {
        this.currentRuns = [];
        this.currentLogContent = null;
        this.selectedLog = null;
        this.init();
    }

    init() {
        this.loadRuns();
        this.bindEvents();
    }

    bindEvents() {
        document.getElementById('refresh-btn').addEventListener('click', () => {
            this.loadRuns();
        });

        document.getElementById('download-btn').addEventListener('click', () => {
            this.downloadCurrentLog();
        });

        document.getElementById('clear-logs-btn').addEventListener('click', () => {
            this.clearAllLogs();
        });

        document.getElementById('runDropdown').addEventListener('change', (e) => {
            this.onRunSelected(e.target.value);
        });

        document.getElementById('logDropdown').addEventListener('change', (e) => {
            this.onLogSelected(e.target.value);
        });
    }

    async loadRuns() {
        try {
            const runDropdown = document.getElementById('runDropdown');
            runDropdown.innerHTML = '<option value="">Loading runs...</option>';
            runDropdown.disabled = true;
            
            const response = await fetch('/api/logs/runs');
            const runs = await response.json();
            
            if (response.ok) {
                this.currentRuns = runs;
                this.populateRunDropdown(runs);
            } else {
                throw new Error(runs.error || 'Failed to load runs');
            }
        } catch (error) {
            console.error('Error loading runs:', error);
            const runDropdown = document.getElementById('runDropdown');
            runDropdown.innerHTML = '<option value="">Error loading runs</option>';
        }
    }

    populateRunDropdown(runs) {
        const runDropdown = document.getElementById('runDropdown');
        
        if (runs.length === 0) {
            runDropdown.innerHTML = '<option value="">No log runs found</option>';
            runDropdown.disabled = true;
            return;
        }

        const options = runs.map(run => 
            `<option value="${run.datetime_str}">${run.datetime} (${run.logs.length} logs)</option>`
        ).join('');

        runDropdown.innerHTML = '<option value="">Select a run...</option>' + options;
        runDropdown.disabled = false;
    }

    onRunSelected(datetimeStr) {
        const logDropdown = document.getElementById('logDropdown');
        
        if (!datetimeStr) {
            logDropdown.innerHTML = '<option value="">Select a run first</option>';
            logDropdown.disabled = true;
            this.clearLogDisplay();
            return;
        }

        const selectedRun = this.currentRuns.find(run => run.datetime_str === datetimeStr);
        if (!selectedRun) {
            logDropdown.innerHTML = '<option value="">Error: Run not found</option>';
            logDropdown.disabled = true;
            return;
        }

        // Populate log dropdown
        const logOptions = selectedRun.logs.map(log => 
            `<option value="${log.classname}">${log.classname}</option>`
        ).join('');

        logDropdown.innerHTML = '<option value="">Select a log file...</option>' + logOptions;
        logDropdown.disabled = false;
        
        this.clearLogDisplay();
    }

    onLogSelected(classname) {
        const runDropdown = document.getElementById('runDropdown');
        const datetimeStr = runDropdown.value;
        
        if (!classname || !datetimeStr) {
            this.clearLogDisplay();
            return;
        }

        this.selectLog(classname, datetimeStr);
    }

    clearLogDisplay() {
        document.getElementById('current-log-title').textContent = 'Select a log to view';
        document.getElementById('log-content-container').innerHTML = 
            '<div class="no-log-selected"><p>Select a run and log file from the dropdowns to view contents.</p></div>';
        document.getElementById('download-btn').style.display = 'none';
    }

    async selectLog(classname, datetime) {
        try {
            // Update UI to show loading
            document.getElementById('current-log-title').textContent = 'Loading...';
            document.getElementById('log-content-container').innerHTML = 
                '<div class="loading">Loading log content...</div>';

            // Load log content
            const response = await fetch(`/api/logs/content?classname=${classname}&datetime=${datetime}`);
            const result = await response.json();

            if (response.ok) {
                this.currentLogContent = result.content;
                this.selectedLog = { classname, datetime };
                this.renderLogContent(classname, datetime, result.content);
                document.getElementById('download-btn').style.display = 'inline-block';
            } else {
                throw new Error(result.error || 'Failed to load log content');
            }
        } catch (error) {
            console.error('Error loading log content:', error);
            document.getElementById('log-content-container').innerHTML = 
                '<div class="error">Error loading log: ' + error.message + '</div>';
            document.getElementById('download-btn').style.display = 'none';
        }
    }

    renderLogContent(classname, datetime, content) {
        document.getElementById('current-log-title').textContent = 
            `${classname} - ${datetime.replace('_', ' ').replace('_', ' ')}`;

        const container = document.getElementById('log-content-container');
        
        // Process log content - convert to HTML with basic highlighting
        const processedContent = this.processLogContent(content);
        
        container.innerHTML = `
            <div class="log-content">
                <pre class="log-text">${processedContent}</pre>
            </div>
        `;
    }

    processLogContent(content) {
        // Basic log processing - escape HTML and add simple highlighting
        let processed = content
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');

        // Add basic log level highlighting
        processed = processed
            .replace(/\b(ERROR|CRITICAL)\b/g, '<span class="log-error">$1</span>')
            .replace(/\b(WARNING|WARN)\b/g, '<span class="log-warning">$1</span>')
            .replace(/\b(INFO)\b/g, '<span class="log-info">$1</span>')
            .replace(/\b(DEBUG)\b/g, '<span class="log-debug">$1</span>');

        // Highlight timestamps (basic pattern)
        processed = processed.replace(
            /(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}[,.]?\d*)/g, 
            '<span class="log-timestamp">$1</span>'
        );

        return processed;
    }

    downloadCurrentLog() {
        if (!this.currentLogContent || !this.selectedLog) {
            return;
        }

        const blob = new Blob([this.currentLogContent], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        
        a.href = url;
        a.download = `${this.selectedLog.classname}_${this.selectedLog.datetime}.log`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    async clearAllLogs() {
        if (!confirm('Are you sure you want to clear all log files and folders? This action cannot be undone.')) {
            return;
        }

        try {
            const response = await fetch('/api/logs/clear', {
                method: 'POST'
            });
            const result = await response.json();

            if (response.ok && result.success) {
                alert('All log files and folders have been cleared successfully.');
                // Refresh the logs view
                this.loadRuns();
                this.clearLogDisplay();
            } else {
                throw new Error(result.error || 'Failed to clear logs');
            }
        } catch (error) {
            console.error('Error clearing logs:', error);
            alert('Error clearing logs: ' + error.message);
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new LogsViewer();
});