let departmentChart;
let categoryChart;
let dailyChart;

const palette = ['#4f46e5', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#14b8a6', '#f97316'];

function buildChart(canvasId, type, labels, values, label, options = {}) {
    const canvas = document.getElementById(canvasId);
    const chartMap = {
        departmentChart,
        categoryChart,
        dailyChart,
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

    if (canvasId === 'departmentChart') departmentChart = instance;
    if (canvasId === 'categoryChart') categoryChart = instance;
    if (canvasId === 'dailyChart') dailyChart = instance;
}

function setSummary(data) {
    document.getElementById('totalHours').textContent = `${data.total_hours}시간`;
    document.getElementById('rangeText').textContent = `${data.range.start} ~ ${data.range.end}`;

    const topDepartment = data.departments[0];
    const topCategory = data.categories[0];

    document.getElementById('topDepartment').textContent = topDepartment ? topDepartment.label : '-';
    document.getElementById('topDepartmentMeta').textContent = topDepartment ? `${topDepartment.value}시간 · ${topDepartment.percent}%` : '데이터 없음';
    document.getElementById('topCategory').textContent = topCategory ? topCategory.label : '-';
    document.getElementById('topCategoryMeta').textContent = topCategory ? `${topCategory.value}시간 · ${topCategory.percent}%` : '데이터 없음';
}

async function loadDashboard() {
    const period = document.getElementById('periodFilter').value;
    const userId = document.getElementById('memberFilter').value;

    const response = await fetch(`/api/dashboard-data?period=${period}&user_id=${userId}`);
    const data = await response.json();

    setSummary(data);

    buildChart(
        'departmentChart',
        'pie',
        data.departments.map(item => `${item.label} (${item.percent}%)`),
        data.departments.map(item => item.value),
        '부서별 시간'
    );

    buildChart(
        'categoryChart',
        'pie',
        data.categories.map(item => `${item.label} (${item.percent}%)`),
        data.categories.map(item => item.value),
        '업무 분류별 시간'
    );

    buildChart(
        'dailyChart',
        'bar',
        data.daily.map(item => item.label),
        data.daily.map(item => item.value),
        '일자별 시간'
    );
}

document.getElementById('loadDashboardBtn').addEventListener('click', loadDashboard);
window.addEventListener('DOMContentLoaded', loadDashboard);
