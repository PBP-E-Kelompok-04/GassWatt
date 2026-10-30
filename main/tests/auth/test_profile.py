import os
import shutil
import tempfile
from io import BytesIO

from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from PIL import Image

NS = "main"
PASSWORD = "Str0ng-pass-123!"
TEMP_MEDIA = tempfile.mkdtemp()

User = get_user_model()


def url(name):
    return reverse(f"{NS}:{name}")


def make_user(email="alice@example.com", username="alice", password=PASSWORD):
    return User.objects.create_user(email=email, username=username, password=password)


def make_image(fmt="PNG", size=(400, 200), color=(200, 30, 30)):
    buf = BytesIO()
    Image.new("RGB", size, color).save(buf, format=fmt)
    ext = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp", "GIF": "gif"}[fmt]
    return SimpleUploadedFile(
        f"test.{ext}", buf.getvalue(), content_type=f"image/{ext}"
    )


def make_upload(img, fmt, **save_kwargs):
    buf = BytesIO()
    img.save(buf, format=fmt, **save_kwargs)
    ext = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}[fmt]
    return SimpleUploadedFile(f"test.{ext}", buf.getvalue(), content_type=f"image/{ext}")


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class ProfileTestBase(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)


class ProfilePageTests(ProfileTestBase):
    def test_anonymous_is_redirected(self):
        self.client.logout()
        response = self.client.get(url("show_profile"))
        self.assertEqual(response.status_code, 302)

    def test_page_renders_for_logged_in_user(self):
        response = self.client.get(url("show_profile"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "profile.html")
        self.assertContains(response, 'id="usernameForm"')
        self.assertContains(response, 'id="passwordForm"')
        self.assertContains(response, 'id="avatarWrapper"')

    def test_page_handles_user_without_username(self):
        self.user.username = None
        self.user.save()
        response = self.client.get(url("show_profile"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'value="None"')


class UpdateUsernameTests(ProfileTestBase):
    def post(self, username):
        return self.client.post(url("update_username"), {"username": username})

    def test_success(self):
        response = self.post("new_name")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "new_name")

    def test_whitespace_is_trimmed(self):
        self.post("   spaced   ")
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "spaced")

    def test_too_short(self):
        response = self.post("ab")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["ok"])

    def test_too_long(self):
        response = self.post("a" * 21)
        self.assertEqual(response.status_code, 400)

    def test_max_length_allowed(self):
        response = self.post("a" * 20)
        self.assertEqual(response.status_code, 200)

    def test_invalid_characters(self):
        for bad in ["has space", "bad<script>", "emoji😀name", "semi;colon"]:
            with self.subTest(bad=bad):
                self.assertEqual(self.post(bad).status_code, 400)

    def test_duplicate_is_rejected_case_insensitively(self):
        make_user(email="bob@example.com", username="Bob")
        response = self.post("bob")
        self.assertEqual(response.status_code, 400)
        self.assertIn("taken", response.json()["error"])
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "alice")

    def test_can_resave_own_username_with_different_case(self):
        response = self.post("ALICE")
        self.assertEqual(response.status_code, 200)

    def test_integrity_error_on_save_is_handled(self):
        from django.db import IntegrityError

        with mock.patch.object(User, "save", side_effect=IntegrityError):
            response = self.post("race_name")
        self.assertEqual(response.status_code, 400)
        self.assertIn("taken", response.json()["error"])

    def test_get_not_allowed(self):
        self.assertEqual(self.client.get(url("update_username")).status_code, 405)

    def test_anonymous_cannot_update(self):
        self.client.logout()
        response = self.post("hacker")
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "alice")

    def test_csrf_is_enforced(self):
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.user)
        response = strict.post(url("update_username"), {"username": "csrf_test"})
        self.assertEqual(response.status_code, 403)


class UpdateAvatarTests(ProfileTestBase):
    def post(self, file=None):
        data = {"pfp": file} if file is not None else {}
        return self.client.post(url("update_avatar"), data)

    def test_success_resizes_to_square_jpeg(self):
        response = self.post(make_image("PNG", size=(400, 200)))
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["ok"])
        self.assertIn("?v=", body["url"])

        self.user.refresh_from_db()
        self.assertTrue(self.user.pfp.name.startswith("pfp/user_"))
        with Image.open(self.user.pfp.path) as saved:
            self.assertEqual(saved.size, (256, 256))
            self.assertEqual(saved.format, "JPEG")

    def test_accepts_jpeg_and_webp(self):
        for fmt in ("JPEG", "WEBP"):
            with self.subTest(fmt=fmt):
                self.assertEqual(self.post(make_image(fmt)).status_code, 200)

    def test_no_file(self):
        response = self.post()
        self.assertEqual(response.status_code, 400)

    def test_file_too_large(self):
        big = SimpleUploadedFile(
            "big.png", b"0" * (2 * 1024 * 1024 + 1), content_type="image/png"
        )
        response = self.post(big)
        self.assertEqual(response.status_code, 400)
        self.assertIn("2 MB", response.json()["error"])

    def test_not_an_image(self):
        fake = SimpleUploadedFile(
            "evil.png", b"<?php echo 'hi'; ?>", content_type="image/png"
        )
        response = self.post(fake)
        self.assertEqual(response.status_code, 400)

    def test_disallowed_format_gif(self):
        response = self.post(make_image("GIF"))
        self.assertEqual(response.status_code, 400)

    def test_old_avatar_is_deleted_on_replace(self):
        self.post(make_image("PNG"))
        self.user.refresh_from_db()
        first_path = self.user.pfp.path
        self.assertTrue(os.path.exists(first_path))

        self.post(make_image("JPEG", color=(10, 10, 200)))
        self.user.refresh_from_db()
        self.assertEqual(
            len([f for f in os.listdir(os.path.dirname(first_path)) if f.startswith(f"user_{self.user.pk}")]),
            1,
        )
        self.assertFalse(os.path.exists(first_path))

    def test_default_image_is_never_deleted(self):
        # A fresh user still points at the shared default; uploading must not
        # try to delete it (it may not exist on disk, and must not error).
        self.assertEqual(self.user.pfp.name, "default.jpg")
        response = self.post(make_image("PNG"))
        self.assertEqual(response.status_code, 200)

    def test_transparent_png_becomes_white_not_black(self):
        upload = make_upload(Image.new("RGBA", (100, 100), (0, 0, 0, 0)), "PNG")
        self.assertEqual(self.post(upload).status_code, 200)
        self.user.refresh_from_db()
        with Image.open(self.user.pfp.path) as saved:
            r, g, b = saved.getpixel((128, 128))
        self.assertTrue(min(r, g, b) > 240)

    def test_exif_rotation_is_applied(self):
        # 200x100: left half red, right half blue, EXIF orientation 6
        # (rotate 90 CW) -> after fixing, red should be on top, blue on bottom.
        img = Image.new("RGB", (200, 100), (255, 0, 0))
        img.paste((0, 0, 255), (100, 0, 200, 100))
        exif = Image.Exif()
        exif[0x0112] = 6
        self.assertEqual(self.post(make_upload(img, "JPEG", exif=exif)).status_code, 200)
        self.user.refresh_from_db()
        with Image.open(self.user.pfp.path) as saved:
            top = saved.getpixel((128, 10))
            bottom = saved.getpixel((128, 245))
        self.assertTrue(top[0] > 150 and top[2] < 100)
        self.assertTrue(bottom[2] > 150 and bottom[0] < 100)

    def test_decompression_bomb_rejected(self):
        with mock.patch.object(Image, "MAX_IMAGE_PIXELS", 100):
            response = self.post(make_image("PNG", size=(400, 200)))
        self.assertEqual(response.status_code, 400)

    def test_get_not_allowed(self):
        self.assertEqual(self.client.get(url("update_avatar")).status_code, 405)

    def test_anonymous_cannot_upload(self):
        self.client.logout()
        response = self.post(make_image("PNG"))
        self.assertEqual(response.status_code, 302)


class ChangePasswordTests(ProfileTestBase):
    NEW = "An0ther-str0ng-pass!"

    def post(self, old=PASSWORD, new1=NEW, new2=None):
        return self.client.post(
            url("change_password"),
            {
                "old_password": old,
                "new_password1": new1,
                "new_password2": new1 if new2 is None else new2,
            },
        )

    def test_success(self):
        response = self.post()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.NEW))

    def test_user_stays_logged_in_after_change(self):
        self.post()
        response = self.client.get(url("show_profile"))
        self.assertEqual(response.status_code, 200)

    def test_can_login_with_new_password_only(self):
        # Assumes USERNAME_FIELD = "email" (matches make_user()).
        self.post()
        self.assertTrue(Client().login(email="alice@example.com", password=self.NEW))
        self.assertFalse(Client().login(email="alice@example.com", password=PASSWORD))

    def test_wrong_current_password(self):
        response = self.post(old="wrong-password")
        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_confirmation_mismatch(self):
        response = self.post(new2="something-else-123!")
        self.assertEqual(response.status_code, 400)
        self.assertIn("do not match", response.json()["errors"][0])

    def test_same_as_current(self):
        response = self.post(new1=PASSWORD)
        self.assertEqual(response.status_code, 400)

    def test_weak_passwords_rejected_by_validators(self):
        # Only meaningful if AUTH_PASSWORD_VALIDATORS is configured (default
        # Django project template does).
        for weak in ["short1", "12345678", "password"]:
            with self.subTest(weak=weak):
                response = self.post(new1=weak)
                self.assertEqual(response.status_code, 400)
                self.assertTrue(len(response.json()["errors"]) >= 1)

    def test_get_not_allowed(self):
        self.assertEqual(self.client.get(url("change_password")).status_code, 405)

    def test_anonymous_cannot_change(self):
        self.client.logout()
        response = self.post()
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))
