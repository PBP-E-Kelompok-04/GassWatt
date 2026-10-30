from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST

User = get_user_model()

USER_DASHBOARD_URL = "main:show_dashboard"
ADMIN_DASHBOARD_URL = "main:admin_dashboard"
LOGIN_URL = "main:show_login"
REGISTER_URL = "main:show_register"


@require_GET
def show_login(request):
    return render(request, "authentication-templates/login.html")

@require_POST
def login_user(request):
    identifier = request.POST.get("identifier", "").strip()
    password = request.POST.get("password", "")

    # Mengecek apabila input adalah username atau email yang ada
    match = User.objects.filter(
        Q(username__iexact=identifier) | Q(email__iexact=identifier)
    ).first()
    login_name = match.get_username() if match else ""

    user = authenticate(request, username=login_name, password=password)
    if user is None:
        messages.error(request, "Username/email atau password invalid.")
        return redirect(LOGIN_URL)

    login(request, user)
    if user.is_staff or user.is_superuser:
        return redirect(ADMIN_DASHBOARD_URL)
    return redirect(USER_DASHBOARD_URL)

@require_GET
def show_register(request):
    return render(request, "authentication-templates/register.html")

@require_POST
def register_user(request):
    username = request.POST.get("username", "").strip()
    email = request.POST.get("email", "").strip().lower()
    password = request.POST.get("password", "")
    confirm_password = request.POST.get("confirm_password", "")

    if not username or not email or not password:
        messages.error(request, "Username, email, dan password dibutuhkan.")
        return redirect(REGISTER_URL)

    if "@" in username:
        messages.error(request, "Username tidak boleh mengandung '@'.")
        return redirect(REGISTER_URL)

    if password != confirm_password:
        messages.error(request, "Password tidak sama.")
        return redirect(REGISTER_URL)

    if User.objects.filter(username__iexact=username).exists():
        messages.error(request, "Username sudah diambil.")
        return redirect(REGISTER_URL)

    if User.objects.filter(email__iexact=email).exists():
        messages.error(request, "Email sudah terdaftar.")
        return redirect(REGISTER_URL)

    try:
        with transaction.atomic():
            User.objects.create_user(username=username, email=email, password=password)
    except IntegrityError:
        # Username atau email sudah terdaftar
        messages.error(request, "Username atau email sudah terdaftar.")
        return redirect(REGISTER_URL)

    messages.success(request, "Akun telah dibuat. Anda bisa login.")
    return redirect(LOGIN_URL)

@require_POST
def logout_user(request):
    logout(request)
    messages.success(request, "Anda telah logout.")
    return redirect(LOGIN_URL)