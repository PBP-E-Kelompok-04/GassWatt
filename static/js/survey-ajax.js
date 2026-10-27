const surveyConfig = document.getElementById('surveyConfig');
const BASE_SURVEY_ENDPOINT = surveyConfig.dataset.listUrl;
const ADD_SURVEY_ENDPOINT = surveyConfig.dataset.addUrl;
const UPDATE_SURVEY_URL = surveyConfig.dataset.editUrlTemplate;
const DELETE_SURVEY_URL = surveyConfig.dataset.deleteUrlTemplate;

let surveyAbortController;
let activeDeleteId = null;

// Elemen DOM State
const loadingState = document.getElementById('loadingState');
const errorState = document.getElementById('errorState');
const emptyState = document.getElementById('emptyState');
const transportTable = document.getElementById('transportTable');
const transportTableBody = document.getElementById('transportTableBody');
const transportTotalEmission = document.getElementById('transportTotalEmission');

// Elemen Modals & Form
const surveyModal = document.getElementById('surveyModal');
const deleteModal = document.getElementById('deleteModal');
const surveyForm = document.getElementById('surveyForm');

// Mengatur Tampilan State Halaman
function displayPageSection({ showLoading = false, showError = false, showEmpty = false, showTable = false }) {
    if (loadingState) loadingState.classList.toggle('hidden', !showLoading);
    if (errorState) errorState.classList.toggle('hidden', !showError);
    if (emptyState) emptyState.classList.toggle('hidden', !showEmpty);
    if (transportTable) transportTable.classList.toggle('hidden', !showTable);
}

// Cookie Reader Helper untuk Token CSRF
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Sanitasi String HTML
function escapeHtml(value) {
    return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
}

// Memposisikan Popover Sejajar dengan Tombol yang Diklik
function positionPopoverRelativeToButton(popoverElement, targetButton) {
    const wrapper = document.getElementById('tableWrapper');
    if (!wrapper || !targetButton) return;

    const wrapperRect = wrapper.getBoundingClientRect();
    const buttonRect = targetButton.getBoundingClientRect();

    const topPosition = buttonRect.bottom - wrapperRect.top + 8;
    const rightPosition = wrapperRect.right - buttonRect.right;

    popoverElement.style.top = `${topPosition}px`;
    popoverElement.style.right = `${rightPosition}px`;
}

// Membangun Baris Tabel Secara Dinamis
function buildSurveyRowElement(item) {
    const tr = document.createElement('tr');
    tr.setAttribute('data-id', item.id);

    const safeMode = escapeHtml(item.mode);
    const safeDistance = escapeHtml(item.distance);
    const formattedEmission = Number(item.daily_emission_co2 || 0).toFixed(2).replace('.', ',');

    tr.innerHTML = `
        <td>${safeMode}</td>
        <td>${safeDistance} Km</td>
        <td>${formattedEmission}</td>
        <td>
            <div class="table-actions">
                <button type="button" class="btn-icon btn-edit" aria-label="Edit">Edit</button>
                <button type="button" class="btn-icon btn-delete" aria-label="Hapus">Hapus</button>
            </div>
        </td>
    `;

    const editButton = tr.querySelector('.btn-edit');
    if (editButton) {
        editButton.addEventListener('click', (e) => openEditSurveyModal(item, e.currentTarget));
    }

    const deleteButton = tr.querySelector('.btn-delete');
    if (deleteButton) {
        deleteButton.addEventListener('click', (e) => openDeleteModal(item.id, e.currentTarget));
    }

    return tr;
}

// Fetch Data Transportasi dari Backend
async function fetchSurveys() {
    if (surveyAbortController) surveyAbortController.abort();
    surveyAbortController = new AbortController();

    try {
        displayPageSection({ showLoading: true });

        const response = await fetch(BASE_SURVEY_ENDPOINT, {
            headers: { 'Accept': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
            signal: surveyAbortController.signal,
        });

        if (!response.ok) throw new Error(`Failed to fetch data (${response.status})`);

        const result = await response.json();
        if (result.status !== 'success') throw new Error(result.message || 'Failed to fetch data');

        if (!result.data || result.data.length === 0) {
            transportTableBody.innerHTML = '';
            transportTotalEmission.textContent = '0,00';
            displayPageSection({ showEmpty: true });
        } else {
            transportTableBody.innerHTML = '';
            let totalEmission = 0;
            result.data.forEach(item => {
                transportTableBody.appendChild(buildSurveyRowElement(item));
                totalEmission += Number(item.daily_emission_co2) || 0;
            });
            transportTotalEmission.textContent = totalEmission.toFixed(2).replace('.', ',');
            displayPageSection({ showTable: true });
        }
    } catch (error) {
        if (error.name === 'AbortError') return;
        console.error('Error loading surveys:', error);
        displayPageSection({ showError: true });
    }
}

// Buka & Tutup Modal Sederhana
function openModal(modal) {
    if (modal) modal.classList.remove('hidden');
}

function closeModal(modal) {
    if (modal) modal.classList.add('hidden');
}

function openEditSurveyModal(item) {
    if (!surveyForm) return;

    document.getElementById('surveyId').value = item.id;
    if (surveyForm.elements.namedItem('transport_mode')) surveyForm.elements.namedItem('transport_mode').value = item.mode_val;
    if (surveyForm.elements.namedItem('daily_distance_km')) surveyForm.elements.namedItem('daily_distance_km').value = item.distance;
    if (surveyForm.elements.namedItem('notes')) surveyForm.elements.namedItem('notes').value = item.notes;

    document.getElementById('modalTitle').textContent = 'Edit Transportasi';
    closeModal(deleteModal);
    openModal(surveyModal);
}

function openDeleteModal(id) {
    activeDeleteId = id;

    deleteModal.dataset.mode = 'transport';
    deleteModal.querySelector('h3').textContent = 'Hapus Data?';
    deleteModal.querySelector('p').textContent = 'Apakah kamu yakin ingin menghapus data transportasi ini?';
    
    closeModal(surveyModal);
    openModal(deleteModal);
}

// Submit Form (Save/Update)
async function handleSurveySubmit(event) {
    event.preventDefault();

    const submitButton = surveyForm.querySelector('button[type="submit"]');
    if (submitButton) submitButton.disabled = true;

    const surveyId = document.getElementById('surveyId').value;
    const targetUrl = surveyId 
        ? UPDATE_SURVEY_URL.replace('00000000-0000-0000-0000-000000000000', surveyId)
        : ADD_SURVEY_ENDPOINT;

    try {
        const response = await fetch(targetUrl, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json'
            },
            body: new FormData(surveyForm)
        });

        const result = await response.json().catch(() => ({}));

        if (response.ok && result.status === 'success') {
            closeModal(surveyModal);
            surveyForm.reset();
            fetchSurveys();
        } else {
            const fieldErrors = result.errors
                ? Object.values(result.errors).flat().join('\n')
                : '';
            alert(fieldErrors || result.message || 'Terjadi kesalahan saat menyimpan data.');
        }
    } catch (error) {
        console.error('Error saving survey:', error);
        alert('Tidak dapat terhubung ke server. Silakan coba lagi.');
    } finally {
        if (submitButton) submitButton.disabled = false;
    }
}

// Submit Delete
async function executeDeleteAjax(event) {
    event.preventDefault();
    if (!activeDeleteId) return;

    const targetUrl = DELETE_SURVEY_URL.replace('00000000-0000-0000-0000-000000000000', activeDeleteId);

    try {
        const response = await fetch(targetUrl, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json'
            }
        });

        const result = await response.json().catch(() => ({}));

        if (response.ok && result.status === 'success') {
            closeModal(deleteModal);
            activeDeleteId = null;
            fetchSurveys();
        } else {
            alert(result.message || 'Gagal menghapus data.');
        }
    } catch (error) {
        console.error('Error deleting survey:', error);
        alert('Tidak dapat terhubung ke server.');
    }
}

// Control Buttons Event Listeners
if (surveyForm) surveyForm.addEventListener('submit', handleSurveySubmit);

const btnConfirmDelete = document.getElementById('btnConfirmDelete');
if (btnConfirmDelete) btnConfirmDelete.addEventListener('click', executeDeleteAjax);

const btnCloseModal = document.getElementById('btnCloseModal');
if (btnCloseModal) btnCloseModal.addEventListener('click', () => closeModal(surveyModal));

const btnCloseIcon = document.getElementById('btnCloseIcon');
if (btnCloseIcon) btnCloseIcon.addEventListener('click', () => closeModal(surveyModal));

// close kalau pencet selain form
if (surveyModal) {
        surveyModal.addEventListener("click", function (event) {
            if (event.target === surveyModal) {
                closeModal(surveyModal);
            }
        });
    }

const btnCancelDelete = document.getElementById('btnCancelDelete');
if (btnCancelDelete) btnCancelDelete.addEventListener('click', () => closeModal(deleteModal));

const btnRetry = document.getElementById('btnRetry');
if (btnRetry) btnRetry.addEventListener('click', fetchSurveys);

const btnOpenAddModal = document.getElementById('btnOpenAddModal');
if (btnOpenAddModal) {
    btnOpenAddModal.addEventListener('click', (e) => {
        if (surveyForm) surveyForm.reset();
        document.getElementById('surveyId').value = '';
        document.getElementById('modalTitle').textContent = 'Tambah Transportasi';
        
        // Posisikan modal di dekat tombol Tambah
        positionPopoverRelativeToButton(surveyModal, e.currentTarget);
        closeModal(deleteModal);
        openModal(surveyModal);
    });
}

// Inisialisasi awal saat halaman dimuat
fetchSurveys();