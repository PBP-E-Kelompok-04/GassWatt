const reusableConfig = document.getElementById('reusableConfig');
const BASE_REUSABLE_ENDPOINT = reusableConfig.dataset.listUrl;
const ADD_REUSABLE_ENDPOINT = reusableConfig.dataset.addUrl;
const UPDATE_REUSABLE_URL = reusableConfig.dataset.editUrlTemplate;
const DELETE_REUSABLE_URL = reusableConfig.dataset.deleteUrlTemplate;

const ZERO_REUSABLE_UUID = '00000000-0000-0000-0000-000000000000';
let reusableSurveyAbortController;
let activeReusableDeleteId = null;

const reusableLoadingState = document.getElementById('reusableLoadingState');
const reusableErrorState = document.getElementById('reusableErrorState');
const reusableEmptyState = document.getElementById('reusableEmptyState');
const reusableTable = document.getElementById('reusableTable');
const reusableTableBody = document.getElementById('reusableTableBody');
const reusableTotalEmission = document.getElementById('reusableTotalEmission');

const reusableModal = document.getElementById('reusableModal');
const reusableDeleteModal = document.getElementById('reusableDeleteModal');
const reusableForm = document.getElementById('reusableForm');
const reusableSurveyId = document.getElementById('reusableSurveyId');
const reusableModalTitle = document.getElementById('reusableModalTitle');

// Panel & tab (urutan tab: 0 = Perangkat Listrik, 1 = Transportasi, 2 = Barang Reusable)
const reusablePanel = document.getElementById('reusablePanel');
const reusableElectricityPanel = document.getElementById('electricityPanel');
const reusableTransportPanel = document.querySelector(
    '.survey-page > section.transport-card:not(#electricityPanel):not(#reusablePanel)'
);
const reusableSurveyTabs = document.querySelectorAll('.survey-tabs .survey-tab');
const reusableTab = reusableSurveyTabs[2];

function displayReusablePageSection({ showLoading = false, showError = false, showEmpty = false, showTable = false }) {
    if (reusableLoadingState) reusableLoadingState.classList.toggle('hidden', !showLoading);
    if (reusableErrorState) reusableErrorState.classList.toggle('hidden', !showError);
    if (reusableEmptyState) reusableEmptyState.classList.toggle('hidden', !showEmpty);
    if (reusableTable) reusableTable.classList.toggle('hidden', !showTable);
}

function formatReusableNumber(value) {
    return (Number(value) || 0).toFixed(3).replace('.', ',');
}

function buildReusableSurveyRowElement(item) {
    const tr = document.createElement('tr');
    tr.setAttribute('data-id', item.id);

    tr.innerHTML = `
        <td>${escapeHtml(item.item)}</td>
        <td>${escapeHtml(item.quantity)}</td>
        <td>${escapeHtml(item.notes || '-')}</td>
        <td>${formatReusableNumber(item.daily_emission_co2)}</td>
        <td>
            <div class="table-actions">
                <button type="button" class="btn-icon btn-edit" aria-label="Edit">Edit</button>
                <button type="button" class="btn-icon btn-delete" aria-label="Hapus">Hapus</button>
            </div>
        </td>
    `;

    const editButton = tr.querySelector('.btn-edit');
    if (editButton) {
        editButton.addEventListener('click', () => openEditReusableModal(item));
    }

    const deleteButton = tr.querySelector('.btn-delete');
    if (deleteButton) {
        deleteButton.addEventListener('click', () => openDeleteReusableModal(item.id));
    }

    return tr;
}

async function fetchReusableSurveys() {
    if (reusableSurveyAbortController) reusableSurveyAbortController.abort();
    reusableSurveyAbortController = new AbortController();

    try {
        displayReusablePageSection({ showLoading: true });

        const response = await fetch(BASE_REUSABLE_ENDPOINT, {
            headers: {
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            signal: reusableSurveyAbortController.signal
        });

        if (!response.ok) throw new Error(`Failed to fetch data (${response.status})`);

        const result = await response.json();
        if (result.status !== 'success' || !Array.isArray(result.data)) {
            throw new Error(result.message || 'Gagal mengambil data barang reusable');
        }

        reusableTableBody.innerHTML = '';
        let totalEmission = 0;

        if (result.data.length === 0) {
            reusableTotalEmission.textContent = formatReusableNumber(0);
            displayReusablePageSection({ showEmpty: true });
        } else {
            result.data.forEach(item => {
                reusableTableBody.appendChild(buildReusableSurveyRowElement(item));
                totalEmission += Number(item.daily_emission_co2) || 0;
            });
            reusableTotalEmission.textContent = formatReusableNumber(totalEmission);
            displayReusablePageSection({ showTable: true });
        }
    } catch (error) {
        if (error.name === 'AbortError') return;
        console.error('Error loading reusable surveys:', error);
        displayReusablePageSection({ showError: true });
    }
}

function openEditReusableModal(item) {
    if (!reusableForm) return;

    reusableForm.reset();
    reusableSurveyId.value = item.id;
    reusableForm.elements.namedItem('item_type').value = item.item_val;
    reusableForm.elements.namedItem('quantity').value = item.quantity;
    reusableForm.elements.namedItem('uses_per_week').value = item.uses_per_week;
    reusableForm.elements.namedItem('notes').value = item.notes || '';

    reusableModalTitle.textContent = 'Edit Barang Reusable';
    closeModal(reusableDeleteModal);
    openModal(reusableModal);
}

function openDeleteReusableModal(id) {
    activeReusableDeleteId = id;
    closeModal(reusableModal);
    openModal(reusableDeleteModal);
}

async function handleReusableSurveySubmit(event) {
    event.preventDefault();

    const submitButton = reusableForm.querySelector('button[type="submit"]');
    if (submitButton.disabled) return;
    submitButton.disabled = true;

    const surveyId = reusableSurveyId.value;
    const targetUrl = surveyId
        ? UPDATE_REUSABLE_URL.replace(ZERO_REUSABLE_UUID, surveyId)
        : ADD_REUSABLE_ENDPOINT;

    try {
        const response = await fetch(targetUrl, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json'
            },
            body: new FormData(reusableForm)
        });

        const result = await response.json().catch(() => ({}));

        if (response.ok && result.status === 'success') {
            closeModal(reusableModal);
            reusableForm.reset();
            reusableSurveyId.value = '';
            fetchReusableSurveys();
        } else {
            const fieldErrors = result.errors
                ? Object.values(result.errors).flat().join('\n')
                : '';
            alert(fieldErrors || result.message || 'Terjadi kesalahan saat menyimpan barang.');
        }
    } catch (error) {
        console.error('Error saving reusable survey:', error);
        alert('Tidak dapat terhubung ke server. Silakan coba lagi.');
    } finally {
        submitButton.disabled = false;
    }
}

async function executeReusableDeleteAjax(event) {
    event.preventDefault();
    if (!activeReusableDeleteId) return;

    const deleteButton = document.getElementById('btnConfirmReusableDelete');
    if (deleteButton.disabled) return;
    deleteButton.disabled = true;

    const targetUrl = DELETE_REUSABLE_URL.replace(ZERO_REUSABLE_UUID, activeReusableDeleteId);

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
            closeModal(reusableDeleteModal);
            activeReusableDeleteId = null;
            fetchReusableSurveys();
        } else {
            alert(result.message || 'Gagal menghapus barang reusable.');
        }
    } catch (error) {
        console.error('Error deleting reusable survey:', error);
        alert('Tidak dapat terhubung ke server.');
    } finally {
        deleteButton.disabled = false;
    }
}

// ---------- Pindah tab ----------
// survey-electricity.js hanya mengatur panel Listrik & Transportasi, jadi di sini
// ditambahkan: tab Reusable menampilkan panelnya, dan tab lain menyembunyikannya.
function showReusablePanel() {
    if (reusableElectricityPanel) reusableElectricityPanel.classList.add('hidden');
    if (reusableTransportPanel) reusableTransportPanel.classList.add('hidden');
    reusablePanel.classList.remove('hidden');
    reusableSurveyTabs.forEach((tab, index) => tab.classList.toggle('active', index === 2));
}

function hideReusablePanel() {
    reusablePanel.classList.add('hidden');
    if (reusableTab) reusableTab.classList.remove('active');
}

if (reusableTab) {
    reusableTab.addEventListener('click', (event) => {
        event.preventDefault();
        showReusablePanel();
    });
}
if (reusableSurveyTabs[0]) reusableSurveyTabs[0].addEventListener('click', hideReusablePanel);
if (reusableSurveyTabs[1]) reusableSurveyTabs[1].addEventListener('click', hideReusablePanel);

// ---------- Event listeners ----------
if (reusableForm) reusableForm.addEventListener('submit', handleReusableSurveySubmit);

const btnConfirmReusableDelete = document.getElementById('btnConfirmReusableDelete');
if (btnConfirmReusableDelete) {
    btnConfirmReusableDelete.addEventListener('click', executeReusableDeleteAjax);
}

const btnCancelReusable = document.getElementById('btnCancelReusable');
if (btnCancelReusable) {
    btnCancelReusable.addEventListener('click', () => closeModal(reusableModal));
}

const btnCloseReusableIcon = document.getElementById('btnCloseReusableIcon');
if (btnCloseReusableIcon) {
    btnCloseReusableIcon.addEventListener('click', () => closeModal(reusableModal));
}

const btnCancelReusableDelete = document.getElementById('btnCancelReusableDelete');
if (btnCancelReusableDelete) {
    btnCancelReusableDelete.addEventListener('click', () => closeModal(reusableDeleteModal));
}

if (reusableModal) {
    reusableModal.addEventListener('click', function (event) {
        if (event.target === reusableModal) closeModal(reusableModal);
    });
}
if (reusableDeleteModal) {
    reusableDeleteModal.addEventListener('click', function (event) {
        if (event.target === reusableDeleteModal) closeModal(reusableDeleteModal);
    });
}

const btnRetryReusable = document.getElementById('btnRetryReusable');
if (btnRetryReusable) btnRetryReusable.addEventListener('click', fetchReusableSurveys);

const btnOpenAddReusableModal = document.getElementById('btnOpenAddReusableModal');
if (btnOpenAddReusableModal) {
    btnOpenAddReusableModal.addEventListener('click', () => {
        reusableForm.reset();
        reusableSurveyId.value = '';
        reusableModalTitle.textContent = 'Tambah Barang Reusable';
        closeModal(reusableDeleteModal);
        openModal(reusableModal);
    });
}

// Inisialisasi awal
if (window.location.hash === '#reusable') showReusablePanel();
fetchReusableSurveys();