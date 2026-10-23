const weatherConfig = document.getElementById("weather-page");

const el = (id) => document.getElementById(id);
const urls = {
    search: weatherConfig.dataset.searchUrl,
    weather: weatherConfig.dataset.weatherUrl,
    list: weatherConfig.dataset.listUrl,
    save: weatherConfig.dataset.saveUrl,
    update: weatherConfig.dataset.updateUrlTemplate,
    activate: weatherConfig.dataset.activateUrlTemplate,
    delete: weatherConfig.dataset.deleteUrlTemplate,
};

const isAuthenticated = weatherConfig.dataset.authenticated === "true";
const REFRESH_MS = 10 * 60 * 1000;

let currentSelected = null;
let currentRecommendations = { energi: [], mobilitas: [], lainnya: [] };
let savedLocations = [];
let searchTimer = null;
let searchController = null;
let weatherController = null;
let searchSequence = 0;
let weatherSequence = 0;
let lastWeatherCheck = 0;
let locationMap = null;
let locationMarker = null;

const csrfToken = () => el("csrf-form")?.querySelector("[name=csrfmiddlewaretoken]")?.value || "";
const urlForId = (template, id) => template.replace("999999", encodeURIComponent(String(id)));
const formatNumber = (value, digits = 1) => {
    if (value === null || value === undefined || value === "" ||
        !Number.isFinite(Number(value))) return "-";
    return new Intl.NumberFormat("id-ID", {
        maximumFractionDigits: digits
    }).format(Number(value));
};
const measure = (value, unit, digits = 1) => {
    const formatted = formatNumber(value, digits);
    return formatted === "-" ? "-" : `${formatted} ${unit}`;
};

function setStatus(message, type = "info") {
    const status = el("weather-status");
    status.textContent = message;
    status.dataset.type = type;
    status.classList.toggle("status-hidden", !message);
}

async function readJson(response) {
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        const details = data.error ||
            (data.errors ? Object.values(data.errors).flat().join(" ") : "Permintaan gagal.");
        throw new Error(details);
    }
    return data;
}

async function postForm(url, fields = {}) {
    const body = new FormData();
    for (const [key, value] of Object.entries(fields)) body.append(key, value);
    return readJson(await fetch(url, {
        method: "POST",
        credentials: "same-origin",
        headers: { "X-CSRFToken": csrfToken() },
        body,
    }));
}

function hideDropdown() {
    el("search-dropdown-results").hidden = true;
    el("search-location-input").setAttribute("aria-expanded", "false");
}

function clearWeatherDisplay() {
    weatherController?.abort();
    weatherSequence++;
    currentRecommendations = { energi: [], mobilitas: [], lainnya: [] };
    el("display-location-name").textContent = "Belum memilih lokasi";
    el("display-temp").textContent = "--°C";
    el("display-condition").textContent = "Pilih lokasi Anda";
    setImage("main-weather-icon", "", "Ikon cuaca");

    updateMetricIcons();
    el("weather-updated").textContent = "Belum ada data cuaca";
    for (const id of ["stat-uv", "stat-rain", "stat-pop", "det-temp",
        "det-humidity", "det-rain", "det-pop", "det-uv", "det-wind", "det-cloud",
        "det-code", "det-time", "det-observed", "det-aqi", "det-no2"]) el(id).textContent = "-";

    if (locationMarker) {
        locationMarker.remove();
        locationMarker = null;
    }
    el("location-map").hidden = true;
    el("map-placeholder").hidden = false;
    el("btn-refresh-weather").disabled = true;
    el("btn-save").disabled = true;
    renderRecommendations(getActiveCategory());
}

function getActiveCategory() {
    return weatherConfig.querySelector(".tab-btn.active")?.dataset.category || "energi";
}

function renderRecommendations(category) {
    const list = el("recommendations-list");
    list.replaceChildren();
    const items = currentRecommendations[category] || [];
    if (!items.length) {
        const empty = document.createElement("div");
        empty.className = "empty-placeholder";
        empty.textContent = currentSelected
            ? "Belum ada rekomendasi khusus untuk kategori ini."
            : "Pilih lokasi untuk mendapatkan rekomendasi ramah lingkungan.";
        list.appendChild(empty);
        return;
    }
    items.forEach((rec) => {
        const box = document.createElement("article");
        box.className = "recommendation-box";
        const icon = document.createElement("img");
        icon.className = "rec-icon";
        if (rec.icon) icon.src = rec.icon;
        icon.alt = "";
        icon.setAttribute("aria-hidden", "true");
        const content = document.createElement("div");
        content.className = "rec-content";
        const heading = document.createElement("h4");
        heading.textContent = rec.title;
        const description = document.createElement("p");
        description.textContent = rec.desc;
        content.append(heading, description);
        box.append(icon, content);
        list.appendChild(box);
    });
}

function updateMap(lat, lon) {
    try {
        const L = window.L;
        if (!L || typeof L.map !== "function") {
            throw new Error("Library peta Leaflet gagal dimuat.");
        }
        const mapElement = el("location-map");
        el("map-placeholder").hidden = true;
        mapElement.hidden = false;

        if (!locationMap) {
            locationMap = L.map(mapElement, { zoomControl: true });
            L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
                maxZoom: 19,
                referrerPolicy: "strict-origin-when-cross-origin",
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'
            }).addTo(locationMap);
            locationMap.attributionControl.setPrefix(false);
        }

        locationMap.setView([lat, lon], 14);
        if (locationMarker) {
            locationMarker.setLatLng([lat, lon]);
        } else {
            locationMarker = L.marker([lat, lon]).addTo(locationMap);
        }
        requestAnimationFrame(() => locationMap.invalidateSize());
    } catch (error) {
        setStatus(`Peta gagal dimuat: ${error.message}`, "error");
    }
}

function selectLocation(location) {
    clearTimeout(searchTimer);
    searchController?.abort();
    searchSequence++;

    currentSelected = null;
    clearWeatherDisplay();

    currentSelected = {
        name: location.name,
        latitude: Number(location.latitude),
        longitude: Number(location.longitude),
        savedId: location.id || null,
    };

    el("search-location-input").value = currentSelected.name;
    el("display-location-name").textContent = currentSelected.name;
    el("gps-status-text").textContent = `Terpilih: ${currentSelected.name}`;
    el("btn-refresh-weather").disabled = false;

    updateSaveButton();
    hideDropdown();
    updateMap(currentSelected.latitude, currentSelected.longitude);
    renderRecommendations(getActiveCategory());
    loadWeatherData();
}

function setImage(id, url, description = "") {
    const img = el(id);
    if (!img) return;
    if (url) img.src = url;
    else img.removeAttribute("src");
    img.alt = description;
}

function updateMetricIcons(icons = {}) {
    weatherConfig.querySelectorAll("img[data-weather-icon]").forEach((img) => {
        const url = icons[img.dataset.weatherIcon] || "";
        if (url) img.src = url;
        else img.removeAttribute("src");
        img.hidden = !url;
    });
}

function renderWeather(data) {
    el("display-temp").textContent = measure(data.temperature, "°C");
    el("display-condition").textContent = data.weather_desc || "-";
    setImage("main-weather-icon", data.weather_icon, data.weather_desc || "Ikon cuaca");
    el("stat-uv").textContent = formatNumber(data.uv_index);
    el("stat-rain").textContent = measure(data.precipitation, "mm");
    el("stat-pop").textContent = measure(data.pop, "%", 0);
    el("det-temp").textContent = measure(data.temperature, "°C");
    el("det-humidity").textContent = measure(data.humidity, "%", 0);
    el("det-rain").textContent = measure(data.precipitation, "mm");
    el("det-pop").textContent = measure(data.pop, "%", 0);
    el("det-uv").textContent = formatNumber(data.uv_index);
    el("det-wind").textContent = measure(data.wind_speed, "km/jam");
    el("det-cloud").textContent = measure(data.cloud_cover, "%", 0);
    el("det-code").textContent = data.weather_code == null
        ? "-" : `${data.weather_code} — ${data.weather_desc}`;
    el("det-time").textContent = data.day_period || "-";
    const readableTime = data.observed_at ? data.observed_at.replace("T", " ") : "-";
    el("det-observed").textContent = readableTime;
    const aqiDisplay = formatNumber(data.aqi, 0);
    el("det-aqi").textContent = aqiDisplay === "-"
        ? "-" : `${aqiDisplay} — ${data.aqi_category || "Tidak diketahui"}`;
    el("det-aqi").title = data.air_quality_time
        ? `Waktu data kualitas udara: ${data.air_quality_time.replace("T", " ")}` : "";
    el("det-no2").textContent = measure(
        data.nitrogen_dioxide, data.no2_unit || "µg/m³"
    );
    el("weather-updated").textContent = `Data ${readableTime} (${data.timezone || "waktu lokal"})`;
    updateMetricIcons(data.icons);
    currentRecommendations = data.recommendations || { energi: [], mobilitas: [], lainnya: [] };
    renderRecommendations(getActiveCategory());
}

async function loadWeatherData() {
    if (!currentSelected) return;
    const mySequence = ++weatherSequence;
    weatherController?.abort();
    weatherController = new AbortController();
    const location = { ...currentSelected };
    const params = new URLSearchParams({ lat: location.latitude, lon: location.longitude });
    setStatus(`Memuat cuaca untuk ${location.name}...`);
    try {
        const data = await readJson(await fetch(`${urls.weather}?${params}`, {
            signal: weatherController.signal, credentials: "same-origin",
        }));
        if (mySequence !== weatherSequence) return; 
        renderWeather(data);
        lastWeatherCheck = Date.now();
        setStatus("");
    } catch (error) {
        if (error.name === "AbortError" || mySequence !== weatherSequence) return;
        setStatus(`Data cuaca belum berhasil diperbarui: ${error.message}`, "error");
    }
}

function updateSaveButton() {
    el("btn-save").disabled = !isAuthenticated || !currentSelected ||
        el("search-location-input").value.trim() !== currentSelected.name;
}

function onSearchInput() {
    const query = el("search-location-input").value.trim();
    clearTimeout(searchTimer);
    searchController?.abort();
    const seq = ++searchSequence;

    updateSaveButton();

    if (query.length < 2) {
        hideDropdown();
        return;
    }
    searchTimer = setTimeout(async () => {
        searchController = new AbortController();
        const dropdown = el("search-dropdown-results");
        try {
            const params = new URLSearchParams({ q: query });
            const data = await readJson(await fetch(`${urls.search}?${params}`, {
                signal: searchController.signal,
            }));
            if (seq !== searchSequence || el("search-location-input").value.trim() !== query) return;
            dropdown.replaceChildren();
            if (!data.results?.length) {
                const note = document.createElement("p");
                note.textContent = "Lokasi tidak ditemukan.";
                dropdown.appendChild(note);
            } else {
                data.results.forEach((location) => {
                    const option = document.createElement("button");
                    option.type = "button";
                    option.setAttribute("role", "option");
                    option.textContent = location.name;
                    option.addEventListener("click", () => selectLocation(location));
                    dropdown.appendChild(option);
                });
            }
            dropdown.hidden = false;
            el("search-location-input").setAttribute("aria-expanded", "true");
        } catch (error) {
            if (error.name !== "AbortError" && seq === searchSequence) {
                setStatus(`Gagal mencari lokasi: ${error.message}`, "error");
                hideDropdown();
            }
        }
    }, 350);
}

function useGPSLocation() {
    if (!navigator.geolocation) {
        setStatus("Perangkat atau browser tidak mendukung GPS.", "error");
        return;
    }
    el("gps-status-text").textContent = "Meminta izin lokasi GPS...";
    navigator.geolocation.getCurrentPosition((position) => {
        searchSequence++;
        clearTimeout(searchTimer);
        searchController?.abort();
        selectLocation({
            name: "Lokasi Saya (GPS)",
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
        });
    }, (error) => {
        el("gps-status-text").textContent = "GPS tidak tersedia atau izin ditolak.";
        setStatus(`Gagal mendapatkan GPS (${error.message}).`, "error");
    }, { enableHighAccuracy: false, timeout: 12000, maximumAge: 300000 });
}

async function loadSavedLocations(restore = false) {
    if (!isAuthenticated) return;
    try {
        const data = await readJson(await fetch(urls.list, { credentials: "same-origin" }));
        savedLocations = data.results || [];
        renderSavedLocations();
        if (restore && !currentSelected && !el("search-location-input").value.trim()) {
            const active = savedLocations.find(loc => loc.is_active);
            if (active) selectLocation(active);
        }
    } catch (error) {
        el("saved-locations-list").textContent = `Tidak bisa memuat lokasi: ${error.message}`;
    }
}

function renderSavedLocations() {
    const list = el("saved-locations-list");
    list.replaceChildren();
    if (!savedLocations.length) {
        const p = document.createElement("p");
        p.textContent = "Belum ada lokasi tersimpan.";
        list.appendChild(p);
        return;
    }
    savedLocations.forEach((loc) => {
        const row = document.createElement("div");
        row.className = `saved-row${loc.is_active ? " is-active" : ""}`;
        const name = document.createElement("span");
        name.className = "saved-name";
        name.textContent = loc.name;
        const makeButton = (label, handler, title) => {
            const btn = document.createElement("button");
            btn.type = "button";
            btn.textContent = label;
            btn.title = title;
            btn.addEventListener("click", handler);
            return btn;
        };
        row.append(name,
            makeButton("Pilih", () => activateSavedLocation(loc), `Aktifkan ${loc.name}`),
            makeButton("Ubah", () => openRenameModal(loc), `Ubah nama ${loc.name}`),
            makeButton("Hapus", () => openDeleteModal(loc), `Hapus ${loc.name}`));
        list.appendChild(row);
    });
}

async function saveCurrentLocation() {
    if (!currentSelected) {
        setStatus("Silakan pilih lokasi dari pencarian atau GPS terlebih dahulu.", "error");
        return;
    }
    if (!isAuthenticated) {
        setStatus("Silakan login untuk menyimpan lokasi.", "error");
        return;
    }
    if (el("search-location-input").value.trim() !== currentSelected.name) {
        setStatus("Pilih lokasi dari hasil pencarian terlebih dahulu.", "error");
        return;
    }
    const location = { ...currentSelected };
    el("btn-save").disabled = true;
    try {
        const result = await postForm(urls.save, {
            name: location.name,
            latitude: location.latitude,
            longitude: location.longitude,
        });
        if (currentSelected && currentSelected.latitude === location.latitude &&
            currentSelected.longitude === location.longitude) {
            currentSelected.savedId = result.location.id;
        }
        await loadSavedLocations();
        setStatus("Lokasi berhasil disimpan dan diaktifkan.");
    } catch (error) {
        setStatus(`Gagal menyimpan lokasi: ${error.message}`, "error");
    } finally {
        updateSaveButton();
    }
}

async function activateSavedLocation(loc) {
    try {
        await postForm(urlForId(urls.activate, loc.id));
        await loadSavedLocations();
        selectLocation({ ...loc, is_active: true });
    } catch (error) {
        setStatus(`Gagal memilih lokasi: ${error.message}`, "error");
    }
}

const renameModal = el("weatherRenameModal");
const deleteModal = el("weatherDeleteModal");
const renameForm = el("weatherRenameForm");
const renameInput = el("weatherRenameName");

let pendingRenameLocation = null;
let pendingDeleteLocation = null;
let activeModal = null;
let previouslyFocused = null;
let modalPending = false;

function showModalError(id, message) {
    const messageElement = el(id);
    messageElement.textContent = message;
    messageElement.hidden = !message;
}

function openModal(modal, focusElement) {
    if (activeModal) closeModal(activeModal);
    previouslyFocused = document.activeElement;
    activeModal = modal;
    modal.hidden = false;
    document.body.classList.add("modal-open");
    focusElement.focus();
}

function closeModal(modal, force = false) {
    if (!modal || modal.hidden || (modalPending && !force)) return;
    modal.hidden = true;
    if (activeModal === modal) activeModal = null;
    document.body.classList.remove("modal-open");
    pendingRenameLocation = null;
    pendingDeleteLocation = null;

    if (previouslyFocused && previouslyFocused.isConnected) {
        previouslyFocused.focus();
    } else {
        const summary = document.querySelector(".saved-locations-panel summary");
        if (summary) summary.focus();
        else el("btn-gps").focus();
    }
    previouslyFocused = null;
}

function openRenameModal(location) {
    pendingRenameLocation = location;
    renameForm.reset();
    renameInput.value = location.name;
    showModalError("weatherRenameError", "");
    openModal(renameModal, renameInput);
}

function openDeleteModal(location) {
    pendingDeleteLocation = location;
    el("weatherDeleteDescription").textContent =
        `Yakin ingin menghapus lokasi “${location.name}”? Tindakan ini tidak dapat dibatalkan.`;
    showModalError("weatherDeleteError", "");
    openModal(deleteModal, el("weatherCancelDelete"));
}

async function submitRenameModal(event) {
    event.preventDefault();
    const location = pendingRenameLocation;
    if (!location) return;

    const newName = renameInput.value.trim();
    if (!newName) {
        showModalError("weatherRenameError", "Nama lokasi tidak boleh kosong.");
        renameInput.focus();
        return;
    }
    if (newName === location.name) {
        closeModal(renameModal);
        return;
    }

    const submitButton = el("weatherConfirmRename");
    submitButton.disabled = true;
    modalPending = true;
    showModalError("weatherRenameError", "");
    try {
        const result = await postForm(urlForId(urls.update, location.id), { name: newName });
        if (currentSelected?.savedId === location.id) {
            currentSelected.name = result.location.name;
            el("display-location-name").textContent = currentSelected.name;
            el("search-location-input").value = currentSelected.name;
            el("gps-status-text").textContent = `Terpilih: ${currentSelected.name}`;
            updateSaveButton();
        }
        await loadSavedLocations();
        closeModal(renameModal, true);
        setStatus("Nama lokasi berhasil diperbarui.");
    } catch (error) {
        showModalError("weatherRenameError", `Gagal mengubah lokasi: ${error.message}`);
    } finally {
        submitButton.disabled = false;
        modalPending = false;
    }
}

async function confirmDeleteModal() {
    const location = pendingDeleteLocation;
    if (!location) return;

    const submitButton = el("weatherConfirmDelete");
    submitButton.disabled = true;
    modalPending = true;
    showModalError("weatherDeleteError", "");
    try {
        await postForm(urlForId(urls.delete, location.id));
        if (currentSelected?.savedId === location.id) {
            currentSelected = null;
            el("search-location-input").value = "";
            el("gps-status-text").textContent = "Gunakan GPS atau cari lokasi di atas";
            clearWeatherDisplay();
        }
        await loadSavedLocations();
        closeModal(deleteModal, true);
        setStatus("Lokasi berhasil dihapus.");
    } catch (error) {
        showModalError("weatherDeleteError", `Gagal menghapus lokasi: ${error.message}`);
    } finally {
        submitButton.disabled = false;
        modalPending = false;
    }
}

function handleModalKeyboard(event) {
    if (!activeModal) return;
    if (event.key === "Escape") {
        event.preventDefault();
        closeModal(activeModal);
        return;
    }
    if (event.key !== "Tab") return;

    const focusable = Array.from(activeModal.querySelectorAll(
        'button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled])'
    )).filter(function (element) { return !element.hidden && element.getClientRects().length > 0; });
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
    }
}

renameForm.addEventListener("submit", submitRenameModal);
el("weatherConfirmDelete").addEventListener("click", confirmDeleteModal);
el("weatherCancelRename").addEventListener("click", function () { closeModal(renameModal); });
el("weatherCancelDelete").addEventListener("click", function () { closeModal(deleteModal); });
renameInput.addEventListener("input", function () { showModalError("weatherRenameError", ""); });
document.addEventListener("keydown", handleModalKeyboard);

function clearSearch() {
    clearTimeout(searchTimer);
    searchController?.abort();
    searchSequence++;
    el("search-location-input").value = "";
    hideDropdown();
    updateSaveButton();
    setStatus("");
    el("search-location-input").focus();
}
el("btn-clear-search").addEventListener("click", clearSearch);
el("btn-clear-search").addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        clearSearch();
    }
});
el("search-location-input").addEventListener("input", onSearchInput);
el("search-location-input").addEventListener("keydown", (event) => {
    if (event.key === "Escape") hideDropdown();
});
document.addEventListener("click", (event) => {
    if (!el("search-location-input").parentElement.contains(event.target)) hideDropdown();
});
el("btn-gps").addEventListener("click", useGPSLocation);
el("btn-save").addEventListener("click", saveCurrentLocation);
el("btn-refresh-weather").addEventListener("click", loadWeatherData);
weatherConfig.querySelectorAll(".tab-btn").forEach(button => button.addEventListener("click", () => {
    weatherConfig.querySelectorAll(".tab-btn").forEach(btn => {
        const selected = btn === button;
        btn.classList.toggle("active", selected);
        btn.setAttribute("aria-pressed", String(selected));
    });
    renderRecommendations(button.dataset.category);
}));
window.setInterval(() => {
    if (currentSelected && !document.hidden) loadWeatherData();
}, REFRESH_MS);
document.addEventListener("visibilitychange", () => {
    if (!document.hidden && currentSelected && Date.now() - lastWeatherCheck >= REFRESH_MS) {
        loadWeatherData();
    }
});

clearWeatherDisplay();
loadSavedLocations(true);
