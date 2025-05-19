const dropdown = document.getElementById('cycleDropdown');
const displayTypeDropdown = document.getElementById('displayType');
const ctx = document.getElementById('temperatureChart').getContext('2d');
let chart;

async function loadCycles() {
    try {
        const res = await fetch('/api/cycles');
        if (!res.ok) throw new Error('Failed to fetch cycles');
        const data = await res.json();

        dropdown.innerHTML = '';
        data.forEach(cycle => {
            const option = document.createElement('option');
            option.textContent = cycle;
            option.value = cycle;
            dropdown.appendChild(option);
        });

        if (data.length > 0) {
            loadCycleData(data[0]);
        }
    } catch (error) {
        console.error('Error loading cycles:', error);
    }
}

async function loadCycleData(cycle_name) {
    try {
        const res = await fetch(`/api/data/${cycle_name}`);
        if (!res.ok) throw new Error('Failed to fetch cycle data');
        const data = await res.json();

        // Get current display type
        const displayType = displayTypeDropdown.value;

        // Debug output to help troubleshoot
        console.log('Raw data received:', data);

        const sensors = {};

        data.forEach(([sensor_id, timestamp, temperature]) => {
            // Filter based on display type
            if (displayType !== 'all') {
                // Skip Sensors that don't match the display type
                // Assuming Sensors contain either "temperature" or "humidity" in their names
                const sensorType = sensor_id.toLowerCase();
                if (displayType === 'temperature' && sensorType.includes('humidity')) return;
                if (displayType === 'humidity' && !sensorType.includes('humidity')) return;
            }

            if (!sensors[sensor_id]) {
                sensors[sensor_id] = { timestamps: [], values: [] };
            }

            // Store the original timestamp string
            sensors[sensor_id].timestamps.push(timestamp);
            sensors[sensor_id].values.push(temperature);
        });

        // Debug output to help troubleshoot
        console.log('Processed sensor data:', sensors);

        const datasets = Object.entries(sensors).map(([sensor, data], index) => ({
            label: sensor,
            data: data.timestamps.map((timestamp, i) => ({
                x: new Date(timestamp),
                y: data.values[i]
            })),
            borderColor: getRandomColor(),
            backgroundColor: getRandomColor(0.1),
            fill: false,
            tension: 0.3,
            pointRadius: 3
        }));

        // Debug output
        console.log('Chart datasets:', datasets);

        updateChart(datasets);
    } catch (error) {
        console.error('Error loading cycle data:', error);
    }
}

function updateChart(datasets) {
    // Get current display type to set Y axis label
    const displayType = displayTypeDropdown.value;
    const yAxisLabel = displayType === 'humidity' ? 'Humidity (%)' : 'Temperature (°C)';

    const config = {
        type: 'line',
        data: {
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                title: {
                    display: true,
                    text: `Sensor ${displayType === 'all' ? 'Data' : displayType.charAt(0).toUpperCase() + displayType.slice(1)} Over Time`
                },
                tooltip: {
                    enabled: true
                },
                legend: {
                    position: 'top',
                }
            },
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'second',
                        displayFormats: {
                            second: 'HH:mm:ss'
                        },
                        tooltipFormat: 'yyyy-MM-dd HH:mm:ss'
                    },
                    title: {
                        display: true,
                        text: 'Time'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: yAxisLabel
                    },
                    beginAtZero: false
                }
            }
        }
    };

    // Destroy existing chart if it exists
    if (chart) {
        chart.destroy();
    }

    // Create new chart
    chart = new Chart(ctx, config);
}

function getRandomColor(alpha = 1) {
    const r = Math.floor(Math.random() * 255);
    const g = Math.floor(Math.random() * 255);
    const b = Math.floor(Math.random() * 255);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

// Event listeners
dropdown.addEventListener('change', () => {
    const cycleId = dropdown.value;
    loadCycleData(cycleId);
});

displayTypeDropdown.addEventListener('change', () => {
    const cycleId = dropdown.value;
    loadCycleData(cycleId);
});

// Delete data button
document.getElementById('deleteData').addEventListener('click', async () => {
    try {
    const cycleName = dropdown.value;
    const res = await fetch(`/api/delete_cycle/${cycleName}`);

    const data = await res.json(); // parse backend response

    if (!res.ok) {
        // show popup on error with backend message
        throw new Error(data.message || 'Failed to delete cycle');
    }

    // show popup on success
    alert(`✅ Success: ${data.message || 'Cycle deleted successfully'}`);

    } catch (err) {
        alert(`❌ Error: ${err.message}`);
    }

});


// Export data button
document.getElementById('exportData').addEventListener('click', async () => {
    try {
        const cycleId = dropdown.value;
        const res = await fetch(`/api/delete_cycle/${cycleId}`);
        if (!res.ok) throw new Error('Failed to fetch data for export');
        const data = await res.json();

        // Convert data to CSV
        const csvContent = 'data:text/csv;charset=utf-8,' +
            'Sensor,Timestamp,Value\n' +
            data.map(row => row.join(',')).join('\n');

        // Create download link
        const encodedUri = encodeURI(csvContent);
        const link = document.createElement('a');
        link.setAttribute('href', encodedUri);
        link.setAttribute('download', `${cycleId}_sensor_data.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    } catch (error) {
        console.error('Error exporting data:', error);
        alert('Failed to export data. Please try again.');
    }
});


// Initialize
window.onload = loadCycles;