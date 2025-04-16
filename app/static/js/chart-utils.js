// Shared between both graph pages
export const chartDefaults = {
    borderWidth: 1,
    fill: false,
    pointRadius: 3
};

export function createBaseChart(ctx, initialData) {
    return new Chart(ctx, {
        type: 'line',
        data: initialData,
        options: {
            responsive: true,
            maintainAspectRatio: false, // Added for better canvas control
            scales: {
                x: {
                    type: 'linear',
                    title: { display: true, text: 'Time (seconds)' }
                },
                y: {
                    title: { display: true, text: 'Temperature (°C)' }
                }
            }
        }
    });
}

export function getRandomColor() {
    return `hsl(${Math.random() * 360}, 100%, 70%)`;
}

export function updateChartInterpolation(chart, method) {
    chart.data.datasets.forEach(dataset => {
        dataset.cubicInterpolationMode = method;
    });
    chart.update();
}