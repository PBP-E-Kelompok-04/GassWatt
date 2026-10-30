function toggleAnswer(id) {
        const card = document.getElementById("faq-card-" + id);
        if (card) {
            card.classList.toggle("expanded");
        }
    }

    function openModalAdd() {
        document.getElementById("modalTitle").innerText = "Tambah FAQ";
        document.getElementById("btnSaveText").innerText = "Simpan FAQ";

        document.getElementById("faqForm").action =
            "{% url 'main:add_faq' %}";

        document.getElementById("inputQuestion").value = "";
        document.getElementById("inputAnswer").value = "";

        document.getElementById("faqModal").classList.add("active");
    }

    function openModalEdit(button) {
        document.getElementById("modalTitle").innerText = "Edit FAQ";
        document.getElementById("btnSaveText").innerText = "Simpan Perubahan";

        document.getElementById("faqForm").action = button.dataset.editUrl;
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