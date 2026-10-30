from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import Client, TestCase, override_settings
from django.urls import reverse

User = get_user_model()

PASSWORD = "Str0ng-Pass!42"

# Parameter untuk mevalidasi password
TEST_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Mengecek apabila halaman berhasil ditampilkan
class PageTests(TestCase):
    def test_login_page_renders(self):
        response = self.client.get(reverse("main:show_login"))
        self.assertEqual(response.status_code, 200)

    def test_register_page_renders(self):
        response = self.client.get(reverse("main:show_register"))
        self.assertEqual(response.status_code, 200)

# Mengecek apabila login berhasil atau tidak valid
class LoginViewTests(TestCase):
    def setUp(self):
        self.url = reverse("main:login_user")
        self.user = User.objects.create_user(
            username="myuser123", email="a@example.com", password=PASSWORD
        )

    def test_login_with_username(self):
        response = self.client.post(
            self.url, {"identifier": "myuser123", "password": PASSWORD}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["redirect_url"], reverse("main:show_dashboard"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)

    def test_login_with_email(self):
        response = self.client.post(
            self.url, {"identifier": "a@example.com", "password": PASSWORD}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])

    def test_login_is_case_insensitive(self):
        for identifier in ("MYUSER123", "A@Example.COM"):
            with self.subTest(identifier=identifier):
                client = Client()
                response = client.post(
                    self.url, {"identifier": identifier, "password": PASSWORD}
                )
                self.assertEqual(response.status_code, 200)

    def test_staff_is_sent_to_admin_dashboard(self):
        User.objects.create_superuser(
            username="root", email="root@example.com", password=PASSWORD
        )
        response = self.client.post(
            self.url, {"identifier": "root", "password": PASSWORD}
        )
        self.assertEqual(response.json()["redirect_url"], reverse("main:admin_dashboard"))

    def test_wrong_password(self):
        response = self.client.post(
            self.url, {"identifier": "myuser123", "password": "wrong-password"}
        )
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertFalse(data["ok"])
        self.assertEqual(
            data["errors"]["__all__"], ["Username/email atau password invalid."]
        )
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_unknown_user_gets_same_error_as_wrong_password(self):
        response = self.client.post(
            self.url, {"identifier": "nobody", "password": PASSWORD}
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json()["errors"]["__all__"],
            ["Username/email atau password invalid."],
        )

    def test_missing_fields_return_per_field_errors(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, 400)
        errors = response.json()["errors"]
        self.assertIn("identifier", errors)
        self.assertIn("password", errors)

    def test_inactive_user_cannot_login(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post(
            self.url, {"identifier": "myuser123", "password": PASSWORD}
        )
        self.assertEqual(response.status_code, 401)

    def test_get_not_allowed(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_csrf_is_enforced(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post(
            self.url, {"identifier": "myuser123", "password": PASSWORD}
        )
        self.assertEqual(response.status_code, 403)


# Mengecek apabila registrasi berhasil atau tidak valid
@override_settings(AUTH_PASSWORD_VALIDATORS=TEST_PASSWORD_VALIDATORS)
class RegisterViewTests(TestCase):
    def setUp(self):
        self.url = reverse("main:register_user")

    def payload(self, **overrides):
        data = {
            "username": "myuser123",
            "email": "a@example.com",
            "password": PASSWORD,
            "confirm_password": PASSWORD,
        }
        data.update(overrides)
        return data

    def test_register_success(self):
        response = self.client.post(self.url, self.payload())
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["redirect_url"], reverse("main:show_login"))
        self.assertTrue(data["message"])

        user = User.objects.get(username="myuser123")
        self.assertEqual(user.email, "a@example.com")
        self.assertTrue(user.check_password(PASSWORD))
        self.assertFalse(user.is_staff)

    def test_email_is_lowercased(self):
        self.client.post(self.url, self.payload(email="A@EXAMPLE.COM"))
        self.assertTrue(User.objects.filter(email="a@example.com").exists())

    def test_register_does_not_log_the_user_in(self):
        self.client.post(self.url, self.payload())
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_missing_fields(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, 400)
        errors = response.json()["errors"]
        self.assertEqual(set(errors), {"username", "email", "password"})
        self.assertEqual(User.objects.count(), 0)

    def test_username_with_at_sign(self):
        response = self.client.post(self.url, self.payload(username="my@user"))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["errors"]["username"],
            ["Username tidak boleh mengandung '@'."],
        )

    def test_username_too_short(self):
        response = self.client.post(self.url, self.payload(username="ab"))
        self.assertEqual(response.status_code, 400)
        self.assertIn("username", response.json()["errors"])

    def test_username_with_invalid_characters(self):
        response = self.client.post(self.url, self.payload(username="my user!"))
        self.assertEqual(response.status_code, 400)
        self.assertIn("username", response.json()["errors"])

    def test_username_too_long(self):
        response = self.client.post(self.url, self.payload(username="a" * 151))
        self.assertEqual(response.status_code, 400)
        self.assertIn("username", response.json()["errors"])

    def test_invalid_email_format(self):
        response = self.client.post(self.url, self.payload(email="not-an-email"))
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.json()["errors"])

    def test_password_mismatch(self):
        response = self.client.post(
            self.url, self.payload(confirm_password="Different-Pass!42")
        )
        self.assertEqual(response.status_code, 400)
        errors = response.json()["errors"]
        self.assertEqual(errors["confirm_password"], ["Password tidak sama."])
        self.assertNotIn("password", errors)

    def test_password_too_short(self):
        response = self.client.post(
            self.url, self.payload(password="Ab1!", confirm_password="Ab1!")
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.json()["errors"])

    def test_password_entirely_numeric(self):
        response = self.client.post(
            self.url, self.payload(password="12345678", confirm_password="12345678")
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.json()["errors"])

    def test_password_too_similar_to_username(self):
        response = self.client.post(
            self.url, self.payload(password="myuser123", confirm_password="myuser123")
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.json()["errors"])

    def test_duplicate_username_is_case_insensitive(self):
        User.objects.create_user(
            username="Budi", email="b@example.com", password=PASSWORD
        )
        response = self.client.post(self.url, self.payload(username="budi"))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["errors"]["username"], ["Username sudah diambil."]
        )

    def test_duplicate_email_is_case_insensitive(self):
        User.objects.create_user(
            username="budi", email="a@example.com", password=PASSWORD
        )
        response = self.client.post(self.url, self.payload(email="A@Example.com"))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["errors"]["email"], ["Email sudah terdaftar."]
        )

    def test_all_field_errors_are_returned_together(self):
        response = self.client.post(
            self.url,
            self.payload(
                username="my@user",
                email="not-an-email",
                password="12345678",
                confirm_password="nope",
            ),
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            set(response.json()["errors"]),
            {"username", "email", "password", "confirm_password"},
        )
        self.assertEqual(User.objects.count(), 0)

    def test_integrity_error_race_returns_conflict(self):
        with patch.object(User.objects, "create_user", side_effect=IntegrityError):
            response = self.client.post(self.url, self.payload())
        self.assertEqual(response.status_code, 409)
        data = response.json()
        self.assertFalse(data["ok"])
        self.assertEqual(
            data["errors"]["__all__"], ["Username atau email sudah terdaftar."]
        )

    def test_get_not_allowed(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_csrf_is_enforced(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post(self.url, self.payload())
        self.assertEqual(response.status_code, 403)
        self.assertEqual(User.objects.count(), 0)

# Mengecek apabila logout berhasil atau tidak valid
class LogoutViewTests(TestCase):
    def setUp(self):
        self.url = reverse("main:logout_user")
        self.user = User.objects.create_user(
            username="myuser123", email="a@example.com", password=PASSWORD
        )

    def test_logout(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["redirect_url"], reverse("main:show_login"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_get_not_allowed(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.assertIn("_auth_user_id", self.client.session)

#Mevalidasi field username, email dan password
@override_settings(AUTH_PASSWORD_VALIDATORS=TEST_PASSWORD_VALIDATORS)
class ValidateFieldViewTests(TestCase):
    def setUp(self):
        self.url = reverse("main:validate_field")
        User.objects.create_user(
            username="Budi", email="budi@example.com", password=PASSWORD
        )

    def check(self, field, value, **extra):
        return self.client.post(self.url, {"field": field, "value": value, **extra})

    def test_available_username_is_ok(self):
        response = self.check("username", "newuser")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True, "errors": {}})

    def test_taken_username_is_case_insensitive(self):
        data = self.check("username", "budi").json()
        self.assertFalse(data["ok"])
        self.assertEqual(data["errors"]["username"], ["Username sudah diambil."])

    def test_username_is_stripped_before_checking(self):
        data = self.check("username", "  budi  ").json()
        self.assertFalse(data["ok"])

    def test_username_with_at_sign(self):
        data = self.check("username", "my@user").json()
        self.assertEqual(
            data["errors"]["username"], ["Username tidak boleh mengandung '@'."]
        )

    def test_username_too_short(self):
        data = self.check("username", "ab").json()
        self.assertFalse(data["ok"])
        self.assertIn("username", data["errors"])

    def test_available_email_is_ok(self):
        data = self.check("email", "new@example.com").json()
        self.assertEqual(data, {"ok": True, "errors": {}})

    def test_taken_email_is_case_insensitive(self):
        data = self.check("email", "BUDI@Example.com").json()
        self.assertEqual(data["errors"]["email"], ["Email sudah terdaftar."])

    def test_invalid_email_format(self):
        data = self.check("email", "not-an-email").json()
        self.assertFalse(data["ok"])
        self.assertIn("email", data["errors"])

    def test_strong_password_is_ok(self):
        data = self.check("password", PASSWORD).json()
        self.assertEqual(data, {"ok": True, "errors": {}})

    def test_weak_password_is_rejected(self):
        data = self.check("password", "12345678").json()
        self.assertFalse(data["ok"])
        self.assertIn("password", data["errors"])

    def test_password_similar_to_username_is_rejected(self):
        data = self.check("password", "newuser123", username="newuser123").json()
        self.assertFalse(data["ok"])
        self.assertIn("password", data["errors"])

    def test_empty_value_reports_required(self):
        data = self.check("username", "").json()
        self.assertEqual(data["errors"]["username"], ["Username dibutuhkan."])

    def test_unknown_field_is_a_bad_request(self):
        response = self.check("is_superuser", "true")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["ok"])

    def test_checking_does_not_create_users(self):
        before = User.objects.count()
        self.check("username", "newuser")
        self.check("email", "new@example.com")
        self.assertEqual(User.objects.count(), before)

    def test_get_not_allowed(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_csrf_is_enforced(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post(self.url, {"field": "username", "value": "newuser"})
        self.assertEqual(response.status_code, 403)