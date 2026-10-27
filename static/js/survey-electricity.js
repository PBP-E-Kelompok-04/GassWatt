const electricityConfig = document.getElementById('electricityConfig');
const BASE_ELECTRICITY_ENDPOINT = electricityConfig.dataset.listUrl;
const ADD_ELECTRICITY_ENDPOINT = electricityConfig.dataset.addUrl;
const UPDATE_ELECTRICITY_URL = electricityConfig.dataset.editUrlTemplate;
const DELETE_ELECTRICITY_URL = electricityConfig.dataset.deleteUrlTemplate;

const ZERO_ELECTRICITY_UUID = '00000000-0000-0000-0000-000000000000';
let electricitySurveyAbortController;
let activeElectricityDeleteId = null;

const electricityLoadingState = document.getElementById('electricityLoadingState');
const electricityErrorState = document.getElementById('electricityErrorState');
const electricityEmptyState = document.getElementById('electricityEmptyState');
const electricityTable = document.getElementById('electricityTable');
const electricityTableBody = document.getElementById('electricityTableBody');
const electricityTotalEmission = document.getElementById('electricityTotalEmission');

const electricityModal = document.getElementById('electricityModal');
const electricityForm = document.getElementById('electricityForm');
const electricitySurveyId = document.getElementById('electricitySurveyId');
const electricityModalTitle = document.getElementById('electricityModalTitle');
const deviceNameGroup = document.getElementById('deviceNameGroup');

const electricityPanel = document.getElementById('electricityPanel');
const transportPanel = document.querySelector(
    '.survey-page > section.transport-card:not(#electricityPanel)'
);
const surveyTabs = document.querySelectorAll('.survey-tabs .survey-tab');
const electricityTab = surveyTabs[0];
const transportTab = surveyTabs[1];

const electricityExampleWatts = {
    lamp: 10,
    fan: 45,
    ac: 900,
    refrigerator: 100,
    television: 80,
    laptop: 65,
    desktop: 200,
    washing_machine: 500,
    other: 100
};

function displayElectricityPageSection({showLoading = false, showError = false, showEmpty = false,showTable = false}) {
    if (electricityLoadingState) electricityLoadingState.classList.toggle('hidden', !showLoading);
    if (electricityErrorState) electricityErrorState.classList.toggle('hidden', !showError);
    if (electricityEmptyState) electricityEmptyState.classList.toggle('hidden', !showEmpty);
    if (electricityTable) electricityTable.classList.toggle('hidden', !showTable);
}

function formatElectricityNumber(value, decimals = 2) {
    return (Number(value) || 0).toFixed(decimals);
}

function buildElectricitySurveyRowElement(item) {
    const tr = document.createElement('tr');
    tr.setAttribute('data-id', item.id);

    const safeName = escapeHtml(item.device_label);
    const quantity = item.quantity;
    const watts = formatElectricityNumber(item.power_watts);
    const hours = item.daily_usage_hours;
    const kwh = formatElectricityNumber(item.daily_consumption_kwh);
    const emission = formatElectricityNumber(item.daily_emission_co2);

    tr.innerHTML = `
        <td>${safeName}</td>
        <td>${quantity}</td>
        <td>${watts}</td>
        <td>${hours}</td>
        <td>${kwh}</td>
        <td>${emission}</td>
        <td>
            <div class="table-actions">
                <button type="button" class="btn-icon btn-edit" aria-label="Edit">Edit</button>
                <button type="button" class="btn-icon btn-delete" aria-label="Hapus">Hapus</button>
            </div>
        </td>
    `;

    const editButton = tr.querySelector('.btn-edit');
    if (editButton) {
        editButton.addEventListener('click', () => openEditElectricityModal(item));
    }

    const deleteButton = tr.querySelector('.btn-delete');
    if (deleteButton) {
        deleteButton.addEventListener('click', () => openDeleteElectricityModal(item.id));
    }

    return tr;
}

async function fetchElectricitySurveys() {
    if (electricitySurveyAbortController) electricitySurveyAbortController.abort();
    electricitySurveyAbortController = new AbortController();

    try {
        displayElectricityPageSection({ showLoading: true });

        const response = await fetch(BASE_ELECTRICITY_ENDPOINT, {
            headers: {
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            signal: electricitySurveyAbortController.signal
        });

        if (!response.ok) throw new Error(`Failed to fetch data (${response.status})`);

        const result = await response.json();
        if (result.status !== 'success' || !Array.isArray(result.data)) {
            throw new Error(result.message || 'Gagal mengambil data perangkat listrik');
        }

        electricityTableBody.innerHTML = '';
        let totalEmission = 0;

        if (result.data.length === 0) {
            electricityTotalEmission.textContent = '0,0000';
            displayElectricityPageSection({ showEmpty: true });
        } else {
            result.data.forEach(item => {
                electricityTableBody.appendChild(buildElectricitySurveyRowElement(item));
                totalEmission += Number(item.daily_emission_co2) || 0;
            });
            electricityTotalEmission.textContent = formatElectricityNumber(totalEmission);
            displayElectricityPageSection({ showTable: true });
        }
    } catch (error) {
        if (error.name === 'AbortError') return;
        console.error('Error loading electricity surveys:', error);
        displayElectricityPageSection({ showError: true });
    }
}

function updateElectricityCustomField() {
    const deviceType = electricityForm.elements.namedItem('device_type');
    const customName = electricityForm.elements.namedItem('device_name');
    const isOther = deviceType.value === 'other';

    deviceNameGroup.classList.toggle('hidden', !isOther);
    customName.required = isOther;
    if (!isOther) customName.value = '';
}

function updateElectricityExamplePower() {
    const deviceType = electricityForm.elements.namedItem('device_type');
    const powerInput = electricityForm.elements.namedItem('power_watts');
    powerInput.value = electricityExampleWatts[deviceType.value] ?? '';
    updateElectricityCustomField();
}

function openEditElectricityModal(item) {
    if (!electricityForm) return;

    electricityForm.reset();
    electricitySurveyId.value = item.id;
    electricityForm.elements.namedItem('device_type').value = item.device_type;
    electricityForm.elements.namedItem('device_name').value = item.device_name || '';
    electricityForm.elements.namedItem('quantity').value = item.quantity;
    electricityForm.elements.namedItem('power_watts').value = item.power_watts;
    electricityForm.elements.namedItem('daily_usage_hours').value = item.daily_usage_hours;
    electricityForm.elements.namedItem('notes').value = item.notes || '';

    updateElectricityCustomField();
    electricityModalTitle.textContent = 'Edit Perangkat Listrik';
    closeModal(deleteModal);
    openModal(electricityModal);
}

function openDeleteElectricityModal(id) {
    activeElectricityDeleteId = id;

    deleteModal.dataset.mode = 'electricity';
    deleteModal.querySelector('h3').textContent = 'Hapus Perangkat?';
    deleteModal.querySelector('p').textContent = 'Yakin ingin menghapus data perangkat listrik ini?';

    closeModal(electricityModal);
    openModal(deleteModal);
}

async function handleElectricitySurveySubmit(event) {
    event.preventDefault();

    const submitButton = electricityForm.querySelector('button[type="submit"]');
    if (submitButton.disabled) return;
    submitButton.disabled = true;

    const surveyId = electricitySurveyId.value;
    const targetUrl = surveyId
        ? UPDATE_ELECTRICITY_URL.replace(ZERO_ELECTRICITY_UUID, surveyId)
        : ADD_ELECTRICITY_ENDPOINT;

    try {
        const response = await fetch(targetUrl, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json'
            },
            body: new FormData(electricityForm)
        });

        const result = await response.json().catch(() => ({}));

        if (response.ok && result.status === 'success') {
            closeModal(electricityModal);
            electricityForm.reset();
            electricitySurveyId.value = '';
            fetchElectricitySurveys();
        } else {
            const fieldErrors = result.errors
                ? Object.values(result.errors).flat().join('\n')
                : '';
            alert(fieldErrors || result.message || 'Terjadi kesalahan saat menyimpan perangkat.');
        }
    } catch (error) {
        console.error('Error saving electricity survey:', error);
        alert('Tidak dapat terhubung ke server. Silakan coba lagi.');
    } finally {
        submitButton.disabled = false;
    }
}

async function executeElectricityDeleteAjax(event) {
    event.preventDefault();
    if (!activeElectricityDeleteId) return;

    const deleteButton = document.getElementById('btnConfirmDelete');
    if (deleteButton.disabled) return;
    deleteButton.disabled = true;

    const targetUrl = DELETE_ELECTRICITY_URL.replace(
        ZERO_ELECTRICITY_UUID,
        activeElectricityDeleteId
    );

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
            activeElectricityDeleteId = null;
            fetchElectricitySurveys();
        } else {
            alert(result.message || 'Gagal menghapus perangkat listrik.');
        }
    } catch (error) {
        console.error('Error deleting electricity survey:', error);
        alert('Tidak dapat terhubung ke server.');
    } finally {
        deleteButton.disabled = false;
    }
}

function selectElectricityTab(showElectricity) {
    electricityPanel.classList.toggle('hidden', !showElectricity);
    transportPanel.classList.toggle('hidden', showElectricity);
    electricityTab.classList.toggle('active', showElectricity);
    transportTab.classList.toggle('active', !showElectricity);
}

if (electricityForm) electricityForm.addEventListener('submit', handleElectricitySurveySubmit);

if (btnConfirmDelete) {
    btnConfirmDelete.addEventListener('click', (event) => {
        if (deleteModal.dataset.mode !== 'electricity') return;
        
        event.stopImmediatePropagation();
        executeElectricityDeleteAjax(event);
    }, true);
}

const btnCancelElectricity = document.getElementById('btnCancelElectricity');
if (btnCancelElectricity) {
    btnCancelElectricity.addEventListener('click', () => closeModal(electricityModal));
}

const btnCloseElectricityIcon = document.getElementById('btnCloseElectricityIcon');
if (btnCloseElectricityIcon) {
    btnCloseElectricityIcon.addEventListener('click', () => closeModal(electricityModal));
}

if (btnCancelDelete) {
    btnCancelDelete.addEventListener('click', () => closeModal(deleteModal));
}

if (electricityModal) {
    electricityModal.addEventListener('click', function (event) {
        if (event.target === electricityModal) closeModal(electricityModal);
    });
}

if (deleteModal) {
    deleteModal.addEventListener('click', function (event) {
        if (event.target === deleteModal) closeModal(deleteModal);
    });
}

const btnRetryElectricity = document.getElementById('btnRetryElectricity');
if (btnRetryElectricity) btnRetryElectricity.addEventListener('click', fetchElectricitySurveys);

const btnOpenAddElectricityModal = document.getElementById('btnOpenAddElectricityModal');
if (btnOpenAddElectricityModal) {
    btnOpenAddElectricityModal.addEventListener('click', () => {
        electricityForm.reset();
        electricitySurveyId.value = '';
        electricityForm.elements.namedItem('quantity').value = 1;
        electricityForm.elements.namedItem('daily_usage_hours').value = 4;
        updateElectricityExamplePower();
        electricityModalTitle.textContent = 'Tambah Perangkat Listrik';
        closeModal(deleteModal);
        openModal(electricityModal);
    });
}

const electricityDeviceType = electricityForm.elements.namedItem('device_type');
if (electricityDeviceType) electricityDeviceType.addEventListener('change', updateElectricityExamplePower);

if (electricityTab) {
    electricityTab.addEventListener('click', (event) => {
        event.preventDefault();
        selectElectricityTab(true);
    });
}

if (transportTab) {
    transportTab.addEventListener('click', (event) => {
        event.preventDefault();
        selectElectricityTab(false);
    });
}

updateElectricityCustomField();
fetchElectricitySurveys();
