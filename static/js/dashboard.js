let chartInstance = null;

async function loadDashboard() {
    const year = document.getElementById('yearSelect').value;
    const month = document.getElementById('monthSelect').value;
    const response = await fetch(`/api/dashboard/${year}/${month}`);
    const data = await response.json();

    const labels = data.map(item => item.engineering);
    const executed = data.map(item => item.executed);
    const targets = data.map(item => item.target);
    const percents = data.map(item => item.percent);

    const totalTarget = targets.reduce((a,b) => a + b, 0);
    const totalExecuted = executed.reduce((a,b) => a + b, 0);
    document.getElementById('totalTarget').textContent = totalTarget;
    document.getElementById('totalExecuted').textContent = totalExecuted;
    document.getElementById('overallPercent').textContent = 
        totalTarget > 0 ? ((totalExecuted/totalTarget)*100).toFixed(2) + '%' : '0%';

    const ctx = document.getElementById('maintenanceChart').getContext('2d');
    if (chartInstance) chartInstance.destroy();
    chartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                { label: 'المنفذ', data: executed, backgroundColor: '#ffc107' },
                { label: 'المستهدف', data: targets, backgroundColor: '#0d6efd' }
            ]
        },
        options: {
            responsive: true,
            plugins: { legend: { labels: { color: '#ffc107' } } },
            scales: {
                y: { beginAtZero: true, ticks: { color: '#ffc107' } },
                x: { ticks: { color: '#ffc107' } }
            }
        }
    });

    const tbody = document.getElementById('tableBody');
    tbody.innerHTML = '';
    data.forEach(item => {
        tbody.innerHTML += `
            <tr>
                <td>${item.engineering}</td>
                <td>${item.target}</td>
                <td>${item.executed}</td>
                <td>${item.percent}%</td>
                <td><a href="/report/${item.engineering_id}/${year}/${month}" class="btn btn-sm btn-warning">PDF</a></td>
            </tr>`;
    });
}

document.addEventListener('DOMContentLoaded', () => {
    loadDashboard();
    // ربط النماذج
    document.getElementById('logForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const response = await fetch('/api/log', {
            method: 'POST',
            body: formData
        });
        if (response.ok) {
            alert('تم الحفظ بنجاح');
            location.reload();
        } else {
            alert('حدث خطأ');
        }
    });
    document.getElementById('targetForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const response = await fetch('/api/target', {
            method: 'POST',
            body: formData
        });
        if (response.ok) {
            alert('تم حفظ المستهدف');
            location.reload();
        } else {
            alert('حدث خطأ');
        }
    });
});