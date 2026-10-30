function toggleAnswer(id) {
        const card = document.getElementById("faq-card-" + id);
        if (card) {
            card.classList.toggle("expanded");
        }
    }

    function openModalAdd() {
        const form = document.getElementById("addfaqForm");

        document.getElementById("modalTitle").innerText = "Tambah FAQ";
        document.getElementById("btnSaveText").innerText = "Simpan FAQ";

        form.action = form.dataset.addUrl;

        document.getElementById("inputQuestion").value = "";
        document.getElementById("inputAnswer").value = "";

        document.getElementById("faqModal").classList.add("active");
    }

    function openModalEdit(button) {
        const form = document.getElementById("addfaqForm");

        document.getElementById("modalTitle").innerText = "Edit FAQ";
        document.getElementById("btnSaveText").innerText = "Simpan Perubahan";

        form.action = button.dataset.editUrl;
        document.getElementById("inputQuestion").value = button.dataset.question;
        document.getElementById("inputAnswer").value = button.dataset.answer;

        document.getElementById("faqModal").classList.add("active");
    }

    function closeModal() {
        document.getElementById("faqModal").classList.remove("active");
    }

    // Tutup modal jika pengguna mengeklik area di luar kotak modal.
    document.getElementById("faqModal").addEventListener("click", function (event) {
        if (event.target === this) {
            closeModal();
        }
    });