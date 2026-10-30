from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

User = get_user_model()


class UserModelTests(TestCase):
    def test_create_user_with_username_email_and_password(self):
        u = User.objects.create_user(
            username="myuser123", email="a@example.com", password="pw12345!"
        )
        self.assertEqual(u.username, "myuser123")
        self.assertEqual(u.email, "a@example.com")
        self.assertTrue(u.check_password("pw12345!"))
        self.assertFalse(u.is_staff)

    def test_email_domain_is_normalized(self):
        u = User.objects.create_user(
            username="myuser123", email="a@EXAMPLE.COM", password="pw12345!"
        )
        self.assertEqual(u.email, "a@example.com")

    def test_email_required(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(
                username="myuser123", email="", password="pw12345!"
            )

    def test_username_required(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(
                username="", email="a@example.com", password="pw12345!"
            )

    def test_email_unique(self):
        User.objects.create_user(
            username="myuser123", email="a@example.com", password="pw12345"
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user(
                username="youruser456", email="a@example.com", password="pw12345"
            )

    def test_username_unique(self):
        User.objects.create_user(
            username="myuser123", email="a@example.com", password="pw12345"
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user(
                username="myuser123", email="b@example.com", password="pw12345"
            )

    def test_superuser_flags(self):
        u = User.objects.create_superuser(
            username="root", email="root@example.com", password="pw12345"
        )
        self.assertTrue(u.is_staff and u.is_superuser)
        self.assertEqual(u.username, "root")
        self.assertEqual(u.email, "root@example.com")

    def test_avatar_is_optional(self):
        u = User.objects.create_user(
            username="myuser123", email="a@example.com", password="pw12345"
        )
        self.assertFalse(u.avatar)

    def test_str_is_email(self):
        u = User.objects.create_user(
            username="myuser123", email="a@example.com", password="pw12345"
        )
        self.assertEqual(str(u), "a@example.com")