const dropdown = document.getElementById('cycleDropdown');
const ctx = document.getElementById('temperatureChart').getContext('2d');
let chart;

async function loadCycles() {
    const res = await fetch('/api/cycles');
    const data = await res.json();

    dropdown.innerHTML = '';
    data.forEach(cycle => {
        const option = document.createElement('option');
        option.textContent = cycle
        dropdown.appendChild(option);
    });

    if (data.length > 0) {
        loadCycleData(data[0].cycle_id);
    }
}

async function loadCycleData(cycle_id) {
    const res = await fetch(`/api/data/${cycle_id}`);
    const data = await res.json();

    const sensors = {};

    data.forEach(reading => {
        if (!sensors[reading.sensor_id]) {
            sensors[reading.sensor_id] = { labels: [], data: [] };
        }
        sensors[reading.sensor_id].labels.push(reading.timestamp);
        sensors[reading.sensor_id].data.push(reading.temperature);
    });

    const datasets = Object.entries(sensors).map(([sensor, obj]) => ({
        label: sensor,
        data: obj.data,
        borderColor: getRandomColor(),
        tension: 0.3
    }));

    if (chart) chart.destroy();
    chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: sensors[Object.keys(sensors)[0]].labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            scales: {
                x: {
                    type: 'time',
                    time: {
                        parser: 'YYYY-MM-DDTHH:mm:ss',
                        tooltipFormat: 'll HH:mm:ss'
                    },
                    title: {
                        display: true,
                        text: 'Timestamp'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Temperature (°C)'
                    }
                }
            }
        }
    });
}

function getRandomColor() {
    return `hsl(${Math.floor(Math.random() * 360)}, 70%, 50%)`;
}

dropdown.addEventListener('change', () => {
    const cycleId = dropdown.value;
    loadCycleData(cycleId);
});

window.onload = loadCycles;
