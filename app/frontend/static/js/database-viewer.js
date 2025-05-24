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
        const calculations = {};

        // Process sensor data
        if (data.sensor_data && Array.isArray(data.sensor_data)) {
            data.sensor_data.forEach(([sensor_id, timestamp, temperature]) => {
                // Filter based on display type
                if (displayType !== 'all') {
                    // Skip Sensors that don't match the display type
                    // Assuming Sensors contain either "temperature" or "humidity" in their names
                    const sensorType = sensor_id.toLowerCase();
                    if (displayType === 'temperature' && sensorType.includes('humidity')) return;
                    if (displayType === 'humidity' && !sensorType.includes('humidity')) return;
                    if (displayType === 'calculations') return; // Skip sensor data when showing only calculations
                }

                if (!sensors[sensor_id]) {
                    sensors[sensor_id] = { timestamps: [], values: [] };
                }

                // Store the original timestamp string
                sensors[sensor_id].timestamps.push(timestamp);
                sensors[sensor_id].values.push(temperature);
            });
        }

        // Process calculation data
        if (data.calculation_data && Array.isArray(data.calculation_data)) {
            data.calculation_data.forEach(([calculation_name, timestamp, pid_output, current_temp, target_temp, error]) => {
                // Filter based on display type - only show calculations if requested
                if (displayType !== 'all' && displayType !== 'calculations') return;

                // Create separate datasets for each calculation metric
                const metrics = {
                    [`${calculation_name}_PID_Output`]: pid_output,
                    [`${calculation_name}_Current_Temp`]: current_temp,
                    [`${calculation_name}_Target_Temp`]: target_temp,
                    [`${calculation_name}_Error`]: error
                };

                Object.entries(metrics).forEach(([metricName, value]) => {
                    if (!calculations[metricName]) {
                        calculations[metricName] = { timestamps: [], values: [] };
                    }
                    calculations[metricName].timestamps.push(timestamp);
                    calculations[metricName].values.push(value);
                });
            });
        }

        // Debug output to help troubleshoot
        console.log('Processed sensor data:', sensors);
        console.log('Processed calculation data:', calculations);

        // Create datasets for sensors
        const sensorDatasets = Object.entries(sensors).map(([sensor, data], index) => ({
            label: sensor,
            data: data.timestamps.map((timestamp, i) => ({
                x: new Date(timestamp),
                y: data.values[i]
            })),
            borderColor: getRandomColor(),
            backgroundColor: getRandomColor(0.1),
            fill: false,
            tension: 0.3,
            pointRadius: 3,
            yAxisID: 'y' // Default y-axis for temperature
        }));

        // Create datasets for calculations
        const calculationDatasets = Object.entries(calculations).map(([calcName, data], index) => {
            const isError = calcName.includes('Error');
            const isPIDOutput = calcName.includes('PID_Output');

            return {
                label: calcName,
                data: data.timestamps.map((timestamp, i) => ({
                    x: new Date(timestamp),
                    y: data.values[i]
                })),
                borderColor: getRandomColor(),
                backgroundColor: getRandomColor(0.1),
                fill: false,
                tension: 0.3,
                pointRadius: 2,
                borderDash: isPIDOutput ? [5, 5] : [], // Dashed line for PID output
                yAxisID: isError ? 'y1' : 'y' // Use separate axis for error values
            };
        });

        // Combine all datasets
        const allDatasets = [...sensorDatasets, ...calculationDatasets];

        // Debug output
        console.log('Chart datasets:', allDatasets);

        updateChart(allDatasets);
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

// Delete data button
document.getElementById('deleteAllData').addEventListener('click', async () => {
    try {
    const res = await fetch(`/api/delete_all_cycle`);

    const data = await res.json(); // parse backend response

    if (!res.ok) {
        // show popup on error with backend message
        throw new Error(data.message || 'Failed to delete all cycles');
    }

    // show popup on success
    alert(`✅ Success: ${data.message || 'Cycles deleted successfully'}`);

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