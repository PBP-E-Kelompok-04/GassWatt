from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_protect

User = get_user_model()

USER_DASHBOARD_URL = "main:show_dashboard"
ADMIN_DASHBOARD_URL = "main:admin_dashboard"

@require_GET
def show_login(request):
    return render(request, "authentication-templates/login.html")


@require_POST
def login_user(request):
    identifier = request.POST.get("identifier", "").strip()
    password = request.POST.get("password", "")

    user = authenticate(request, username=identifier, password=password)
    if user is None:
        messages.error(request, "Username atau password invalid.")
        return redirect("main:show_login")

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
        return redirect("main:show_register")

    if "@" in username:
        messages.error(request, "Username tidak boleh mengandung '@'.")
        return redirect("main:show_register")

    if password != confirm_password:
        messages.error(request, "Password tidak sama.")
        return redirect("main:show_register")

    if User.objects.filter(username__iexact=username).exists():
        messages.error(request, "Username sudah diambil.")
        return redirect("main:show_register")

    if User.objects.filter(email__iexact=email).exists():
        messages.error(request, "Email sudah terdaftar.")
        return redirect("main:show_register")

    User.objects.create_user(username=username, email=email, password=password)
    messages.success(request, "Akun telah dibuat. Anda bisa login.")
    return redirect("main:show_login")


@require_POST
@csrf_protect
def logout_user(request):
    logout(request)
    messages.success(request, "Anda telah logout.")
    return redirect("main:show_login")