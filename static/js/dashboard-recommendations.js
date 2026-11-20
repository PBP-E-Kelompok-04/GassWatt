document.addEventListener("DOMContentLoaded", async function () {
    const recommendationList = document.getElementById("recommendationList");
    if (!recommendationList) return;

    function renderMessage(message) {
        const item = document.createElement("div");
        item.className = "recommendation-item";
        item.textContent = message;
        recommendationList.replaceChildren(item);
    }

    try {
        const response = await fetch(recommendationList.dataset.apiUrl);
        if (!response.ok) {
            throw new Error("Gagal mengambil rekomendasi.");
        }

        const result = await response.json();
        if (result.status !== "success" || !Array.isArray(result.data)) {
            throw new Error("Format data rekomendasi tidak valid.");
        }

        if (result.data.length === 0) {
            renderMessage("Belum ada rekomendasi untuk saat ini.");
            return;
        }

        const cards = document.createDocumentFragment();
        result.data.forEach(function (recommendation) {
            const item = document.createElement("div");
            item.className = "recommendation-item";
            item.textContent = recommendation;
            cards.appendChild(item);
        });
        recommendationList.replaceChildren(cards);
    } catch (error) {
        console.error("Error Dashboard Recommendations:", error);
        renderMessage("Rekomendasi gagal dimuat. Silakan coba muat ulang halaman.");
    }
});
