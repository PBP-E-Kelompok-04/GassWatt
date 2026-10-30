from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST
from main.views.view_decorators import redirect_if_authenticated
from django.views.decorators.cache import never_cache

User = get_user_model()

USER_DASHBOARD_URL = "main:show_dashboard"
ADMIN_DASHBOARD_URL = "main:admin_dashboard"
LOGIN_URL = "main:show_login"
REGISTER_URL = "main:show_register"

USERNAME_MIN_LENGTH = 3

NON_FIELD = "__all__"
LIVE_FIELDS = ("username", "email", "password")


def _json_errors(errors, status=400):
    # Menampilkan error json
    """Error response: {"ok": false, "errors": {"field": ["message", ...]}}"""
    return JsonResponse({"ok": False, "errors": errors}, status=status)


def _field_errors(field_name, value):
    # Helper untuk menampilkan error
    try:
        User._meta.get_field(field_name).run_validators(value)
    except ValidationError as exc:
        return list(exc.messages)
    return []


# Validasi tiap field dengan pesan _field_errors
def _username_errors(username):
    if not username:
        return ["Username dibutuhkan."]
    if "@" in username:
        return ["Username tidak boleh mengandung '@'."]
    if len(username) < USERNAME_MIN_LENGTH:
        return [f"Username minimal {USERNAME_MIN_LENGTH} karakter."]
    # Panjang maksimal dan karakter yang diizinkan (aturan bawaan model User)
    model_errors = _field_errors("username", username)
    if model_errors:
        return model_errors
    if User.objects.filter(username__iexact=username).exists():
        return ["Username sudah diambil."]
    return []


def _email_errors(email):
    if not email:
        return ["Email dibutuhkan."]
    # Format email (aturan bawaan model User)
    model_errors = _field_errors("email", email)
    if model_errors:
        return model_errors
    if User.objects.filter(email__iexact=email).exists():
        return ["Email sudah terdaftar."]
    return []


def _password_errors(password, username="", email=""):
    if not password:
        return ["Password dibutuhkan."]
    # Memakai AUTH_PASSWORD_VALIDATORS di settings.py, termasuk pengecekan
    # kemiripan dengan username/email.
    try:
        validate_password(password, user=User(username=username, email=email))
    except ValidationError as exc:
        return list(exc.messages)
    return []


# Views

@never_cache
@redirect_if_authenticated
@require_GET
def show_login(request):
    return render(request, "authentication-templates/login.html")

@never_cache
@redirect_if_authenticated
@require_POST
def login_user(request):
    identifier = request.POST.get("identifier", "").strip()
    password = request.POST.get("password", "")

    errors = {}
    if not identifier:
        errors["identifier"] = ["Username atau email dibutuhkan."]
    if not password:
        errors["password"] = ["Password dibutuhkan."]
    if errors:
        return _json_errors(errors)

    # Mengecek apabila input adalah username atau email yang ada
    match = User.objects.filter(
        Q(username__iexact=identifier) | Q(email__iexact=identifier)
    ).first()
    login_name = match.get_username() if match else ""

    user = authenticate(request, username=login_name, password=password)
    if user is None:
        return _json_errors(
            {NON_FIELD: ["Username/email atau password invalid."]}, status=401
        )

    login(request, user)

    target = ADMIN_DASHBOARD_URL if (user.is_staff or user.is_superuser) else USER_DASHBOARD_URL
    return JsonResponse({"ok": True, "redirect_url": reverse(target)})

@never_cache
@redirect_if_authenticated
@require_GET
def show_register(request):
    return render(request, "authentication-templates/register.html")


@require_POST
def validate_field(request):
    # Hanya menerima field username, email dan password
    field = request.POST.get("field", "")
    value = request.POST.get("value", "")


    if field == "username":
        found = _username_errors(value.strip())
    elif field == "email":
        found = _email_errors(value.strip().lower())
    elif field == "password":
        found = _password_errors(
            value,
            username=request.POST.get("username", "").strip(),
            email=request.POST.get("email", "").strip().lower(),
        )
    else:
        # Unknown field akan return 400
        return _json_errors({NON_FIELD: ["Field tidak dikenal."]})

    return JsonResponse({"ok": not found, "errors": {field: found} if found else {}})

@never_cache
@redirect_if_authenticated
@require_POST
def register_user(request):
    username = request.POST.get("username", "").strip()
    email = request.POST.get("email", "").strip().lower()
    password = request.POST.get("password", "")
    confirm_password = request.POST.get("confirm_password", "")

    errors = {}

    for name, found in (
        ("username", _username_errors(username)),
        ("email", _email_errors(email)),
        ("password", _password_errors(password, username=username, email=email)),
    ):
        if found:
            errors[name] = found

    if password and password != confirm_password:
        errors["confirm_password"] = ["Password tidak sama."]

    if errors:
        return _json_errors(errors)

    try:
        with transaction.atomic():
            User.objects.create_user(username=username, email=email, password=password)
    except IntegrityError:
        # Username atau email sudah terdaftar (race condition)
        return _json_errors(
            {NON_FIELD: ["Username atau email sudah terdaftar."]}, status=409
        )

    return JsonResponse(
        {
            "ok": True,
            "message": "Akun telah dibuat. Anda bisa login.",
            "redirect_url": reverse(LOGIN_URL),
        },
        status=201,
    )


@require_POST
def logout_user(request):
    logout(request)
    return redirect(LOGIN_URL)