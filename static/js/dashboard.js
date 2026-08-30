let chartInstance = null;

async function loadDashboard() {
    const year = document.getElementById('yearSelect').value;
    const month = document.getElementById('monthSelect').value;
    const response = await fetch(`/api/dashboard/${year}/${month}`);
    const data = await response.json();

    const labels = data.map(item => item.engineering);
    const executed = data.map(item => item.executed);
    const targets = data.map(item => item.target);

        const totalTarget = targets.reduce((a,b) => a + b, 0);
    const totalExecuted = executed.reduce((a,b) => a + b, 0);
    
    // النسبة الإجمالية = متوسط نسب الهندسات
    const avgPercent = data.length > 0 ? 
        (data.reduce((sum, item) => sum + item.percent, 0) / data.length).toFixed(2) : 0;
    
    document.getElementById('totalTarget').textContent = totalTarget;
    document.getElementById('totalExecuted').textContent = totalExecuted;
    document.getElementById('overallPercent').textContent = avgPercent + '%';

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

async function loadDetails() {
    const year = document.getElementById('yearSelect').value;
    const month = document.getElementById('monthSelect').value;
    
    try {
        const response = await fetch(`/api/dashboard_details/${year}/${month}`);
        const data = await response.json();
        
        const tbody = document.getElementById('detailsTableBody');
        tbody.innerHTML = '';
        
        data.forEach(comp => {
            comp.engineerings.forEach((eng, index) => {
                const barColor = eng.percent >= 100 ? 'bg-success' : 
                                eng.percent >= 50 ? 'bg-warning' : 
                                eng.percent > 0 ? 'bg-danger' : 'bg-secondary';
                
                tbody.innerHTML += `
                    <tr>
                        ${index === 0 ? `<td rowspan="${comp.engineerings.length}" class="text-warning fw-bold align-middle">${comp.component_name}</td>` : ''}
                        <td>${eng.engineering_name}</td>
                        <td>${eng.target}</td>
                        <td>${eng.executed}</td>
                        <td>
                            <div class="progress" style="height: 20px; min-width: 80px;">
                                <div class="progress-bar ${barColor}" 
                                     role="progressbar" 
                                     style="width: ${Math.min(eng.percent, 100)}%;">
                                    ${eng.percent}%
                                </div>
                            </div>
                        </td>
                    </tr>
                `;
            });
        });
    } catch (error) {
        document.getElementById('detailsTableBody').innerHTML = `
            <tr><td colspan="5" class="text-center text-danger">خطأ في تحميل البيانات</td></tr>
        `;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadDashboard();
    loadDetails();
    
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

// ================== المساعد الذكي ==================
function toggleAssistant() {
    const panel = document.getElementById('aiAssistantPanel');
    if (panel.style.display === 'none') {
        panel.style.display = 'flex';
        panel.style.flexDirection = 'column';
    } else {
        panel.style.display = 'none';
    }
}

async function sendAIMessage() {
    const input = document.getElementById('aiInput');
    const message = input.value.trim();
    if (!message) return;
    
    const messagesDiv = document.getElementById('aiMessages');
    
    messagesDiv.innerHTML += `<div class="ai-message user">${message}</div>`;
    input.value = '';
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    
    const loadingId = 'loadingMsg_' + Date.now();
    messagesDiv.innerHTML += `<div class="ai-message bot" id="${loadingId}">جاري التفكير...</div>`;
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    
    try {
        const response = await fetch('/api/assistant', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message: message })
        });
        
        const data = await response.json();
        
        const loadingMsg = document.getElementById(loadingId);
        if (loadingMsg) loadingMsg.remove();
        
        messagesDiv.innerHTML += `<div class="ai-message bot">${data.response}</div>`;
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    } catch (error) {
        const loadingMsg = document.getElementById(loadingId);
        if (loadingMsg) loadingMsg.remove();
        messagesDiv.innerHTML += `<div class="ai-message bot">حدث خطأ: ${error.message}</div>`;
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }
}

document.addEventListener('DOMContentLoaded', function() {
    const aiInput = document.getElementById('aiInput');
    if (aiInput) {
        aiInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendAIMessage();
            }
        });
    }
});