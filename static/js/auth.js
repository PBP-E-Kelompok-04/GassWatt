(function () {
	"use strict";

	var GENERIC_ERROR = "Terjadi kesalahan. Coba lagi.";
	var NETWORK_ERROR = "Tidak dapat terhubung ke server. Periksa koneksi Anda.";
	var PASSWORD_MISMATCH = "Password tidak sama.";

	// Lama jeda berhenti mengetik sebelum pengecekan langsung dikirim (ms).
	var VALIDATE_DELAY = 500;

	// form -> fungsi yang membatalkan pengecekan langsung yang tertunda / sedang berjalan
	var liveValidators = new WeakMap();

	// Helper

	function getCookie(name) {
		var cookies = document.cookie ? document.cookie.split("; ") : [];
		for (var i = 0; i < cookies.length; i++) {
			var parts = cookies[i].split("=");
			if (parts[0] === name) {
				return decodeURIComponent(parts.slice(1).join("="));
			}
		}
		return "";
	}

	function csrfToken(form) {
		var cookie = getCookie("csrftoken");
		if (cookie) return cookie;
		var input = form && form.querySelector('input[name="csrfmiddlewaretoken"]');
		return input ? input.value : "";
	}

	function debounce(fn, wait) {
		var timer = null;
		function debounced() {
			var context = this;
			var args = arguments;
			clearTimeout(timer);
			timer = setTimeout(function () {
				timer = null;
				fn.apply(context, args);
			}, wait);
		}
		debounced.cancel = function () {
			clearTimeout(timer);
			timer = null;
		};
		return debounced;
	}

	async function readJson(response) {
		try {
			return await response.json();
		} catch (e) {
			return null; // misalnya halaman HTML 403
		}
	}

	// Ttampilan Error

	function clearFieldErrors(form, field) {
		var container = form.querySelector('[data-error-for="' + field + '"]');
		if (container) {
			container.textContent = "";
			container.hidden = true;
		}
		var input = form.querySelector('[name="' + field + '"]');
		if (input) {
			input.removeAttribute("aria-invalid");
			input.classList.remove("is-invalid");
		}
	}

	function clearErrors(form) {
		form.querySelectorAll("[data-error-for]").forEach(function (el) {
			el.textContent = "";
			el.hidden = true;
		});
		form.querySelectorAll("[aria-invalid]").forEach(function (el) {
			el.removeAttribute("aria-invalid");
			el.classList.remove("is-invalid");
		});
		var success = form.querySelector("[data-success]");
		if (success) {
			success.textContent = "";
			success.hidden = true;
		}
	}

	function appendMessages(container, messages) {
		container.hidden = false;
		messages.forEach(function (message) {
			var line = document.createElement("div");
			line.textContent = message; // pakai textContent, jangan innerHTML
			container.appendChild(line);
		});
	}

	function showFieldErrors(form, field, messages) {
		if (!Array.isArray(messages)) messages = [String(messages)];

		var container =
			form.querySelector('[data-error-for="' + field + '"]') ||
			form.querySelector('[data-error-for="__all__"]');
		if (container) appendMessages(container, messages);

		if (field !== "__all__") {
			var input = form.querySelector('[name="' + field + '"]');
			if (input) {
				input.setAttribute("aria-invalid", "true");
				input.classList.add("is-invalid");
			}
		}
	}

	function showErrors(form, errors) {
		Object.keys(errors).forEach(function (field) {
			showFieldErrors(form, field, errors[field]);
		});
		var firstInvalid = form.querySelector(".is-invalid");
		if (firstInvalid) firstInvalid.focus();
	}

	// pengecekan langsung

	function setupLiveValidation(form) {
		var url = form.dataset.validateUrl;
		if (!url) return;

		var state = {}; // per field: { lastValue, controller }
		var debouncers = [];

		function cancelAll() {
			debouncers.forEach(function (d) {
				d.cancel();
			});
			Object.keys(state).forEach(function (field) {
				if (state[field].controller) state[field].controller.abort();
			});
		}
		liveValidators.set(form, cancelAll);

		async function check(input) {
			var field = input.name;
			var value = input.value;
			var st = state[field] || (state[field] = {});

			// Tidak ada perubahan sejak pengecekan terakhir: jangan tanya server lagi.
			if (value === st.lastValue) return;
			st.lastValue = value;

			// Nilai yang lebih baru membuat request sebelumnya yang masih berjalan tidak berlaku.
			if (st.controller) st.controller.abort();
			clearFieldErrors(form, field);

			// Pesan "wajib diisi" ditampilkan saat submit, bukan saat pengguna masih mengetik.
			if (!value.trim()) return;

			var controller = new AbortController();
			st.controller = controller;

			var body = new FormData();
			body.append("field", field);
			body.append("value", value);
			if (field === "password") {
				// Server menolak password yang terlalu mirip dengan username/email.
				["username", "email"].forEach(function (name) {
					var other = form.elements[name];
					if (other) body.append(name, other.value);
				});
			}

			try {
				var response = await fetch(url, {
					method: "POST",
					body: body,
					headers: {
						"X-CSRFToken": csrfToken(form),
						Accept: "application/json",
					},
					credentials: "same-origin",
					signal: controller.signal,
				});
				var data = await readJson(response);
				if (controller.signal.aborted) return; // digantikan request baru atau form sudah dikirim
				if (data && data.errors && data.errors[field]) {
					showFieldErrors(form, field, data.errors[field]);
				}
			} catch (e) {
				// Jika jaringan gagal, diam saja (submit akan memvalidasi lagi)
				// dan izinkan nilai yang sama dicoba ulang.
				if (e.name !== "AbortError") st.lastValue = null;
			}
		}

		// Konfirmasi password dibandingkan di browser, tidak perlu request.
		function checkConfirm() {
			var password = form.elements["password"];
			var confirm = form.elements["confirm_password"];
			if (!password || !confirm) return;
			clearFieldErrors(form, "confirm_password");
			if (confirm.value && password.value !== confirm.value) {
				showFieldErrors(form, "confirm_password", [PASSWORD_MISMATCH]);
			}
		}
		var debouncedConfirm = debounce(checkConfirm, VALIDATE_DELAY);
		debouncers.push(debouncedConfirm);

		form.querySelectorAll("[data-validate]").forEach(function (input) {
			var isConfirm = input.name === "confirm_password";

			if (!isConfirm) {
				var debounced = debounce(function () {
					check(input);
				}, VALIDATE_DELAY);
				debouncers.push(debounced);

				input.addEventListener("input", function () {
					clearFieldErrors(form, input.name); // jangan tampilkan pesan lama
					debounced();
				});
				// Saat keluar dari field, langsung dicek tanpa menunggu.
				input.addEventListener("blur", function () {
					debounced.cancel();
					check(input);
				});
			}

			if (isConfirm || input.name === "password") {
				input.addEventListener("input", debouncedConfirm);
				input.addEventListener("blur", function () {
					debouncedConfirm.cancel();
					checkConfirm();
				});
			}
		});
	}

	// kirim form

	async function submitAuthForm(form) {
		var submit = form.querySelector('[type="submit"]');
		var redirecting = false;

		// Hentikan pengecekan langsung agar tidak menimpa hasil submit.
		var cancelLive = liveValidators.get(form);
		if (cancelLive) cancelLive();

		clearErrors(form);
		if (submit) submit.disabled = true;

		try {
			var formData = new FormData(form);
			formData.delete("csrfmiddlewaretoken");

			var response = await fetch(form.action, {
				method: "POST",
				body: formData,
				headers: {
					"X-CSRFToken": csrfToken(form),
					Accept: "application/json",
				},
				credentials: "same-origin",
			});
			var data = await readJson(response);

			if (data && data.ok) {
				var success = form.querySelector("[data-success]");
				if (data.message && success) {
					success.textContent = data.message;
					success.hidden = false;
				}
				redirecting = true;
				// Jeda singkat hanya jika ada pesan untuk dibaca.
				setTimeout(
					function () {
						window.location.href = data.redirect_url;
					},
					data.message ? 1200 : 0
				);
			} else if (data && data.errors) {
				showErrors(form, data.errors);
			} else {
				showErrors(form, { __all__: [GENERIC_ERROR] });
			}
		} catch (e) {
			showErrors(form, { __all__: [NETWORK_ERROR] });
		} finally {
			if (submit && !redirecting) submit.disabled = false;
		}
	}

	// inisialisasi

	document.addEventListener("submit", function (event) {
		var form = event.target;
		if (form && form.matches && form.matches("form[data-auth-form]")) {
			event.preventDefault();
			submitAuthForm(form);
		}
	});

	function init() {
		document
			.querySelectorAll("form[data-auth-form][data-validate-url]")
			.forEach(setupLiveValidation);
	}

	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", init);
	} else {
		init();
	}
})();