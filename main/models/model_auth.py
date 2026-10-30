from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.contrib.auth.validators import ASCIIUsernameValidator
from django.db import models


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Field email harus di-set")

        username = extra_fields.get("username")
        if username is not None and not str(username).strip():
            extra_fields["username"] = None

        user = self.model(
            email=self.normalize_email(email),
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser harus is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser harus is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True,
        validators=[ASCIIUsernameValidator()],
    )
    email = models.EmailField(unique=True)
    pfp = models.ImageField(upload_to="pfp/", default='default.jpg')

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    objects = UserManager()

    def __str__(self):
        return self.email.split('@')[0]