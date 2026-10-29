document.addEventListener("DOMContentLoaded", function () {
    // ==========================================
    // 1. LINE CHART (Statistik Tren Pengguna)
    // ==========================================

    const trendCanvas = document.getElementById('userTrendChart');
    const filterSelect = document.getElementById('trendFilterSelect');

    if (!trendCanvas || !filterSelect) return;

    // Parsing data dari dataset HTML
    const monthlyLabels = JSON.parse(trendCanvas.dataset.monthlyLabels || '[]');
    const monthlyUsers = JSON.parse(trendCanvas.dataset.monthlyUsers || '[]');
    const dailyLabels = JSON.parse(trendCanvas.dataset.dailyLabels || '[]');
    const dailyActivities = JSON.parse(trendCanvas.dataset.dailyActivities || '[]');

    const ctx = trendCanvas.getContext('2d');

    // Gradient Hijau Transparan
    const gradient = ctx.createLinearGradient(0, 0, 0, 280);
    gradient.addColorStop(0, 'rgba(0, 168, 45, 0.25)');
    gradient.addColorStop(1, 'rgba(0, 168, 45, 0.0)');

    let chartInstance = null;

    function renderTrendChart(mode) {
        const isMonthly = mode === 'monthly';
        const labels = isMonthly ? monthlyLabels : dailyLabels;
        const dataValues = isMonthly ? monthlyUsers : dailyActivities;
        const datasetLabel = isMonthly ? 'Pengguna Aktif' : 'Aktivitas Harian';

        if (chartInstance) {
            chartInstance.destroy();
        }

        chartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: datasetLabel,
                    data: dataValues,
                    borderColor: '#00a82d',
                    backgroundColor: gradient,
                    borderWidth: 3,
                    fill: true,
                    tension: 0.35,
                    pointRadius: 4,
                    pointBackgroundColor: '#00a82d',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return ` ${context.dataset.label}: ${context.raw}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { color: '#8c8c8c' }
                    },
                    y: {
                        beginAtZero: true,
                        grid: { color: '#f0f0f0' },
                        ticks: { precision: 0, color: '#8c8c8c' }
                    }
                }
            }
        });
    }

    // Render Awal Mode Bulanan
    renderTrendChart('monthly');

    // Event Listener Perubahan Filter
    filterSelect.addEventListener('change', function () {
        renderTrendChart(this.value);
    });
});




// ==========================================
// 2. DONUT CHART (Kategori Emisi Terbesar)
// ==========================================
document.addEventListener("DOMContentLoaded", function () {
    
    const canvas = document.getElementById('emisiCategoryChart');
    if (!canvas) return;

    // Bersihkan string dan ubah ke float
    const parseValue = (val) => {
        if (!val) return 0;
        const cleaned = val.toString().replace(',', '.');
        return parseFloat(cleaned) || 0;
    };

    const dataListrik = parseValue(canvas.dataset.listrik);
    const dataTransport = parseValue(canvas.dataset.transport);
    const dataReusable = parseValue(canvas.dataset.reusable);

    const total = dataListrik + dataTransport + dataReusable;

    // Jika total emisi ada (>0), pakai data asli. Jika benar-benar 0, pakai abu-abu
    const chartData = total > 0 ? [dataListrik, dataTransport, dataReusable] : [1, 0, 0];
    const chartColors = total > 0 
        ? ['#00a82d', '#0085d3', '#ffb319'] 
        : ['#e2e8f0', '#e2e8f0', '#e2e8f0'];

    const ctx = canvas.getContext('2d');

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Perangkat Listrik', 'Transportasi', 'Barang Reusable'],
            datasets: [{
                data: chartData,
                backgroundColor: chartColors,
                borderWidth: total > 0 ? 2 : 0,
                borderColor: '#ffffff',
                hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            cutout: '68%',
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    enabled: total > 0,
                    callbacks: {
                        label: function(context) {
                            return ` ${context.label}: ${context.raw} kg CO₂e`;
                        }
                    }
                }
            }
        }
    });
});