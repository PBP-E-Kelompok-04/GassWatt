let selectedUserId = null;

// Filter Pencarian dan Status Client-Side
function filterTable() {
    const searchValue = document.getElementById('searchInput').value.toLowerCase();
    const filterValue = document.getElementById('statusFilter').value;
    const rows = document.querySelectorAll('.user-row');

    rows.forEach(row => {
        const text = row.innerText.toLowerCase();
        const status = row.getAttribute('data-status');

        const matchesSearch = text.includes(searchValue);
        const matchesStatus = (filterValue === 'all') || (status === filterValue);

        row.style.display = (matchesSearch && matchesStatus) ? '' : 'none';
    });
}

// Fungsi Helper Ambil CSRF Token Cookie Django
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

// Modal Konfirmasi
function confirmDelete(id, name) {
    selectedUserId = id;
    document.getElementById('deleteUserName').innerText = name;
    document.getElementById('deleteModal').classList.add('active');
}

function closeModal() {
    document.getElementById('deleteModal').classList.remove('active');
    selectedUserId = null;
}

// Eksekusi AJAX Delete ke Backend Django
function executeDelete() {
    if (!selectedUserId) return;

    fetch(`/kelola-pengguna/delete/${selectedUserId}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // Hapus baris tabel dari DOM tanpa reload halaman
            const targetRow = document.getElementById(`user-row-${selectedUserId}`);
            if (targetRow) targetRow.remove();
            
            closeModal();
        } else {
            alert(data.message);
            closeModal();
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Terjadi kesalahan saat menghapus pengguna.');
        closeModal();
    });
}
