const ctx = document.getElementById('myChart').getContext('2d');
const points = [];
const history = [];
let startTime = null;
let xRange = 2 * 60; // Default x-range in seconds (12 hours)
let unsavedChanges = false;
let measurementInterval = null;

const myChart = new Chart(ctx, {
    type: 'line',
    data: { labels: [], datasets: [] },
    options: {
        responsive: true,
        animation: { duration: 0 },
        scales: {
            x: {
                type: 'linear',
                position: 'bottom',
                min: 0,
                max: xRange,
                title: { display: true, text: 'Time (seconds)' }
            },
            y: {
                min: -20,
                max: 180,
                title: { display: true, text: 'Temperature (°C)' }
            }
        },
        onClick: (event) => {
            const canvasPosition = Chart.helpers.getRelativePosition(event, myChart);
            let x = myChart.scales.x.getValueForPixel(canvasPosition.x);
            let y = myChart.scales.y.getValueForPixel(canvasPosition.y);

            x = Math.round(x / 5) * 5;
            y = Math.round(y / 1) * 1;

            addPoints(x, y);
        }
    }
});

window.addEventListener('beforeunload', function (event) {
    if (unsavedChanges) {
        const message = "You have unsaved changes. Are you sure you want to leave?";
        event.returnValue = message; // Standard for most browsers
        return message; // Some browsers require returning the message
    }
});

document.addEventListener('DOMContentLoaded', updateUndoButtonState);
document.getElementById('submit').addEventListener('click', submitPoint);
document.getElementById('interpolationMethod').addEventListener('change', updateChart);
document.getElementById('undoButton').addEventListener('click', undoLastPoint);
document.getElementById('clearPoints').addEventListener('click', clearPoints);
document.getElementById('sendPointsToServer').addEventListener('click', sendPointsToServer);
document.getElementById('pointInput').addEventListener('input', updateUndoButtonState);

function updateChart() {
    const interpolationMethod = document.getElementById('interpolationMethod').value;
    myChart.data.datasets.forEach(dataset => {
        dataset.cubicInterpolationMode = interpolationMethod;
        dataset.data.sort((a, b) => a.x - b.x); // Sort by x value
    });
    myChart.update();
}

function updateXRange() {
    const xRangeInput = document.getElementById('xRange').value;
    xRange = xRangeInput * 60; // Convert hours to seconds
    myChart.options.scales.x.max = xRange;
    updateChart();
}

function submitPoint(event) {
    event.preventDefault();
    const input = document.getElementById('pointInput').value.trim();
    const [x, y] = input.split(',').map(Number);
    addPoints(x, y);
}

function addPoints(x, y) {
    if (isNaN(x) || isNaN(y)) return;

    const validationMessage = document.getElementById('validationMessage');
    points.push({ x, y });
    history.push({ x, y });
    points.sort((a, b) => a.x - b.x);

    if (!myChart.data.datasets.find(ds => ds.label === 'Desired flow')) {
        myChart.data.datasets.push({
            label: 'Desired flow',
            data: [],
            borderColor: 'rgba(75, 192, 192, 1)',
            borderWidth: 1,
            fill: false,
            cubicInterpolationMode: 'default'
        });
    }

    const userDataSet = myChart.data.datasets.find(ds => ds.label === 'Desired flow');
    userDataSet.data.push({ x, y });
    updateChart();
    updateUndoButtonState();
}

function undoLastPoint() {
    if (history.length > 0) {
        const lastPoint = history.pop();
        const userDataSet = myChart.data.datasets.find(ds => ds.label === 'Desired flow');

        if (userDataSet) {
            const index = userDataSet.data.findIndex(p => p.x === lastPoint.x && p.y === lastPoint.y);
            if (index !== -1) {
                userDataSet.data.splice(index, 1);
                points.splice(points.findIndex(p => p.x === lastPoint.x && p.y === lastPoint.y), 1);
            }
        }

        if (history.length === 0) unsavedChanges = false;

        updateChart();
    } else {
        alert('No points to undo.');
    }

    updateUndoButtonState();
}

function updateUndoButtonState() {
    const undoButton = document.getElementById('undoButton');
    undoButton.disabled = history.length === 0;
}

function clearPoints() {
    points.length = 0;
    history.length = 0;
    myChart.data.datasets.forEach(dataset => dataset.data = []);
    startTime = null;

    updateChart();
    updateUndoButtonState();
    unsavedChanges = false;
}

function exportGraphToJSON() {
    const graphData = {
        interpolationMethod: document.getElementById('interpolationMethod').value,
        datasets: myChart.data.datasets.map(dataset => ({
            label: dataset.label,
            data: dataset.data,
            borderColor: dataset.borderColor,
            borderWidth: dataset.borderWidth,
            cubicInterpolationMode: dataset.cubicInterpolationMode
        }))
    };

    const jsonString = JSON.stringify(graphData, null, 2);
    const blob = new Blob([jsonString], { type: 'application/json' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    unsavedChanges = false;
    link.download = 'graph_data.json';
    link.click();
}

function importGraphFromJSON(event) {
    const file = event.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            const jsonData = JSON.parse(e.target.result);
            document.getElementById('interpolationMethod').value = jsonData.interpolationMethod;
            myChart.data.datasets = jsonData.datasets.map(dataset => ({
                label: dataset.label,
                data: dataset.data,
                borderColor: dataset.borderColor,
                borderWidth: dataset.borderWidth,
                cubicInterpolationMode: dataset.cubicInterpolationMode
            }));
            updateChart();
        };
        reader.readAsText(file);
    }
}

function getRandomColor() {
    return '#' + Math.floor(Math.random() * 16777215).toString(16);
}


function getGraphData() {
    return myChart.data.datasets.map(dataset => ({
        label: dataset.label,
        data: dataset.data
    }));
}

function sendPointsToServer() {
    const graphData = getGraphData();
    fetch('/store-graph-data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(graphData)
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(errorData => alert(errorData.error));
        }
        window.location.href = '/display-graph';
    })
    .catch(console.error);
}

checkServerConnection();
