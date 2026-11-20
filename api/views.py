import time

from django.contrib.auth import login, logout, update_session_auth_hash
from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .permissions import IsAnonymous
from .serializers import (
    NON_FIELD, ChangePasswordSerializer, LoginSerializer, RegisterSerializer,
    UpdateAvatarSerializer, UpdateUsernameSerializer, UserSerializer,
    ValidateFieldSerializer,
)

USER_DASHBOARD_URL = "main:show_dashboard"
ADMIN_DASHBOARD_URL = "main:admin_dashboard"
LOGIN_URL = "main:show_login"
DEFAULT_PFP = "default.jpg"


def _bad(serializer, code=status.HTTP_400_BAD_REQUEST):
    return Response({"ok": False, "errors": serializer.errors}, status=code)


# ---------- /api/sessions/  (login = create session, logout = delete session) ----------
@method_decorator(never_cache, name="dispatch")
class SessionAPI(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAnonymous()]
        return [IsAuthenticated()]

    def post(self, request):
        s = LoginSerializer(data=request.data, context={"request": request})
        if not s.is_valid():
            return _bad(s, 401 if NON_FIELD in s.errors else 400)
        user = s.validated_data["user"]
        login(request._request, user)
        target = ADMIN_DASHBOARD_URL if (user.is_staff or user.is_superuser) else USER_DASHBOARD_URL
        return Response(
            {"ok": True, "redirect_url": reverse(target), "user": UserSerializer(user).data},
            status=status.HTTP_201_CREATED)

    def delete(self, request):
        logout(request._request)
        return Response({"ok": True, "redirect_url": reverse(LOGIN_URL)})


# ---------- /api/users/  (create user = register) ----------
@method_decorator(never_cache, name="dispatch")
class UsersAPI(APIView):
    permission_classes = [IsAnonymous]

    def post(self, request):
        s = RegisterSerializer(data=request.data)
        if not s.is_valid():
            return _bad(s)
        try:
            with transaction.atomic():
                s.save()
        except IntegrityError:
            return Response(
                {"ok": False, "errors": {NON_FIELD: ["Username atau email sudah terdaftar."]}},
                status=status.HTTP_409_CONFLICT)
        return Response(
            {"ok": True, "message": "Akun telah dibuat. Anda bisa login.", "redirect_url": reverse(LOGIN_URL)},
            status=status.HTTP_201_CREATED)


# ---------- /api/validate-field/ ----------
class ValidateFieldAPI(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        s = ValidateFieldSerializer(data=request.data)
        if not s.is_valid():
            return _bad(s)
        found = s.validated_data["found"]
        field = s.validated_data["field"]
        return Response({"ok": not found, "errors": {field: found} if found else {}})


# ---------- /api/users/me/  (read, update, delete own account) ----------
class MeAPI(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        return Response({"ok": True, "user": UserSerializer(request.user).data})

    def patch(self, request):
        has_username = "username" in request.data
        has_pfp = "pfp" in request.data
        if not (has_username or has_pfp):
            return Response(
                {"ok": False, "errors": {NON_FIELD: ["Tidak ada data untuk diubah."]}}, status=400)

        ctx = {"request": request}
        errors = {}
        s_user = UpdateUsernameSerializer(data=request.data, context=ctx) if has_username else None
        s_pfp = UpdateAvatarSerializer(data=request.data, context=ctx) if has_pfp else None
        if s_user and not s_user.is_valid():
            errors.update(s_user.errors)
        if s_pfp and not s_pfp.is_valid():
            errors.update(s_pfp.errors)
        if errors:
            return Response({"ok": False, "errors": errors}, status=400)

        user = request.user
        out = {"ok": True}

        if s_user:
            user.username = s_user.validated_data["username"]
            try:
                with transaction.atomic():
                    user.save(update_fields=["username"])
            except IntegrityError:
                return Response(
                    {"ok": False, "errors": {"username": ["Username sudah diambil."]}}, status=400)
            out["username"] = user.username

        if s_pfp:
            old_name = user.pfp.name if user.pfp else None
            content = s_pfp.validated_data["pfp"]
            user.pfp.save(content.name, content, save=True)
            if old_name and old_name != DEFAULT_PFP:   # never delete the shared default
                user.pfp.storage.delete(old_name)
            out["url"] = f"{user.pfp.url}?v={int(time.time())}"

        out["message"] = (
            "Profil berhasil diubah." if (s_user and s_pfp)
            else "Username berhasil diubah." if s_user
            else "Foto profil berhasil diubah.")
        return Response(out)

    def delete(self, request):
        # Require the password so a hijacked session can't delete the account.
        if not request.user.check_password(request.data.get("password", "")):
            return Response(
                {"ok": False, "errors": {"password": ["Password salah."]}}, status=400)
        user = request.user
        old_name = user.pfp.name if getattr(user, "pfp", None) else None
        logout(request._request)
        user.delete()
        if old_name and old_name != DEFAULT_PFP:
            try:
                user.pfp.storage.delete(old_name)
            except Exception:
                pass
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------- /api/users/me/password/ ----------
class PasswordAPI(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def put(self, request):
        s = ChangePasswordSerializer(data=request.data, context={"request": request})
        if not s.is_valid():
            return _bad(s)
        request.user.set_password(s.validated_data["new_password1"])
        request.user.save(update_fields=["password"])
        update_session_auth_hash(request._request, request.user)
        return Response({"ok": True, "message": "Password berhasil diubah."})