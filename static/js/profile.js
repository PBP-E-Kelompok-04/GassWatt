document.addEventListener("DOMContentLoaded", () => {
    const root = document.getElementById("profilePage");
    const csrf = document.querySelector('meta[name="csrf-token"]').content;
    const urls = {
        username: root.dataset.urlUsername,
        avatar: root.dataset.urlAvatar,
        password: root.dataset.urlPassword,
    };

    // textContent only, so server messages can't inject HTML
    function showMessage(el, ok, text) {
        el.className = "form-message " + (ok ? "success" : "error");
        el.replaceChildren();
        const items = Array.isArray(text) ? text : [text];
        if (items.length > 1) {
            const ul = document.createElement("ul");
            items.forEach(t => {
                const li = document.createElement("li");
                li.textContent = t;
                ul.appendChild(li);
            });
            el.appendChild(ul);
        } else {
            el.textContent = items[0];
        }
    }

    // API errors look like {errors: {field: [msgs]}} or {detail: "..."}; flatten to a list
    function errorMessages(data, fallback) {
        const out = [];
        if (data && data.errors) {
            Object.values(data.errors).forEach(v => out.push(...(Array.isArray(v) ? v : [v])));
        }
        if (data && data.error) out.push(data.error);
        if (data && data.detail) out.push(data.detail);
        return out.length ? out : [fallback];
    }

    async function send(method, url, formData) {
        try {
            const res = await fetch(url, {
                method: method,
                headers: { "X-CSRFToken": csrf, "X-Requested-With": "XMLHttpRequest" },
                body: formData,
                credentials: "same-origin",
            });
            return await res.json();
        } catch {
            return { ok: false, error: "Terjadi kesalahan jaringan atau server." };
        }
    }

    // ---- Avatar ----
    const wrapper = document.getElementById("avatarWrapper");
    const input = document.getElementById("avatarInput");
    const preview = wrapper.querySelector(".profile-avatar");
    const avatarMsg = document.getElementById("avatarMessage");

    wrapper.addEventListener("click", () => input.click());
    wrapper.addEventListener("keydown", e => {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); input.click(); }
    });

    input.addEventListener("change", async () => {
        const file = input.files[0];
        if (!file) return;
        if (file.size > 2 * 1024 * 1024) {
            showMessage(avatarMsg, false, "Ukuran gambar maksimal 2 MB.");
            input.value = "";
            return;
        }

        const fd = new FormData();
        fd.append("pfp", file);
        wrapper.style.opacity = ".6";
        const data = await send("PATCH", urls.avatar, fd);
        wrapper.style.opacity = "";
        input.value = "";

        if (data.ok) {
            // server already adds ?v=<timestamp> for cache busting
            document.querySelectorAll(".profile-avatar").forEach(img => {
                img.src = data.url;
            });
            showMessage(avatarMsg, true, data.message);
        } else {
            showMessage(avatarMsg, false, errorMessages(data, "Gagal mengubah foto profil."));
        }
    });

    // ---- Username ----
    const usernameForm = document.getElementById("usernameForm");
    const usernameMsg = document.getElementById("usernameMessage");

    usernameForm.addEventListener("submit", async e => {
        e.preventDefault();
        const btn = usernameForm.querySelector("button");
        btn.disabled = true;
        const data = await send("PATCH", urls.username, new FormData(usernameForm));
        btn.disabled = false;

        if (data.ok) {
            document.querySelectorAll(".user-name").forEach(el => el.textContent = data.username);
            showMessage(usernameMsg, true, data.message);
        } else {
            showMessage(usernameMsg, false, errorMessages(data, "Gagal mengubah username."));
        }
    });

    // ---- Password ----
    const passwordForm = document.getElementById("passwordForm");
    const passwordMsg = document.getElementById("passwordMessage");

    passwordForm.addEventListener("submit", async e => {
        e.preventDefault();
        const btn = passwordForm.querySelector("button");
        btn.disabled = true;
        const data = await send("PUT", urls.password, new FormData(passwordForm));
        btn.disabled = false;

        if (data.ok) {
            passwordForm.reset();
            showMessage(passwordMsg, true, data.message);
        } else {
            showMessage(passwordMsg, false, errorMessages(data, "Gagal mengubah password."));
        }
    });
});