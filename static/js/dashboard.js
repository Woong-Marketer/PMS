let categoryChart;

const palette = ['#4f46e5', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#14b8a6', '#f97316'];

function buildChart(canvasId, type, labels, values, label, options = {}) {
    const canvas = document.getElementById(canvasId);
    const chartMap = {
        categoryChart,
    };
    if (chartMap[canvasId]) {
        chartMap[canvasId].destroy();
    }

    const instance = new Chart(canvas, {
        type,
        data: {
            labels,
            datasets: [{
                label,
                data: values,
                backgroundColor: type === 'bar' ? '#4f46e5' : palette,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: type !== 'bar'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.label}: ${context.raw}시간`;
                        }
                    }
                }
            },
            scales: type === 'bar' ? {
                y: { beginAtZero: true }
            } : {},
            ...options
        }
    });

    if (canvasId === 'categoryChart') categoryChart = instance;
}

async function loadDashboard() {
    const period = document.getElementById('periodFilter').value;
    const userId = document.getElementById('memberFilter').value;

    const response = await fetch(`/api/dashboard-data?period=${period}&user_id=${userId}`);
    const data = await response.json();

    buildChart(
        'categoryChart',
        'pie',
        data.categories.map(item => `${item.label} (${item.percent}%)`),
        data.categories.map(item => item.value),
        '업무 분류별 시간'
    );
}

document.getElementById('loadDashboardBtn').addEventListener('click', loadDashboard);
window.addEventListener('DOMContentLoaded', loadDashboard);
