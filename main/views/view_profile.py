import uuid
from io import BytesIO

from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.validators import ASCIIUsernameValidator
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_POST
from PIL import Image, ImageOps

User = get_user_model()

USERNAME_MIN, USERNAME_MAX = 3, 20          # max matches the model field
MAX_AVATAR_BYTES = 2 * 1024 * 1024          # 2 MB
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
AVATAR_SIZE = 256
DEFAULT_PFP = "default.jpg"


def _flatten_to_rgb(img):
    """Convert to RGB, compositing transparency onto white (not black)."""
    has_alpha = img.mode in ("RGBA", "LA") or (
        img.mode == "P" and "transparency" in img.info
    )
    if has_alpha:
        img = img.convert("RGBA")
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.getchannel("A"))
        return background
    return img.convert("RGB")


@login_required
def show_profile(request):
    return render(request, "dashboard-templates/profile.html")


@login_required
@require_POST
def update_username(request):
    username = request.POST.get("username", "").strip()

    if not (USERNAME_MIN <= len(username) <= USERNAME_MAX):
        return JsonResponse(
            {"ok": False, "error": f"Username harus berjumlah {USERNAME_MIN}-{USERNAME_MAX} karakter."},
            status=400,
        )
    try:
        ASCIIUsernameValidator()(username)
    except ValidationError:
        return JsonResponse(
            {"ok": False, "error": "Hanya huruf, angka and @ . + - _ diperbolehkan."},
            status=400,
        )
    if User.objects.filter(username__iexact=username).exclude(pk=request.user.pk).exists():
        return JsonResponse({"ok": False, "error": "Username sudah diambil."}, status=400)

    request.user.username = username
    try:
        # atomic() so an IntegrityError doesn't poison an outer transaction
        with transaction.atomic():
            request.user.save(update_fields=["username"])
    except IntegrityError:
        # Lost a race with another request that grabbed the same name.
        return JsonResponse({"ok": False, "error": "Username sudah diambil."}, status=400)
    return JsonResponse({"ok": True, "username": username, "message": "Username berhasil diubah."})


@login_required
@require_POST
def update_avatar(request):
    file = request.FILES.get("pfp")
    if not file:
        return JsonResponse({"ok": False, "error": "No file uploaded."}, status=400)
    if file.size > MAX_AVATAR_BYTES:
        return JsonResponse({"ok": False, "error": "Gambar maksimal 2 MB."}, status=400)

    try:
        img = Image.open(file)
        img.verify()
        file.seek(0)
        img = Image.open(file)                      # must reopen after verify()
        if img.format not in ALLOWED_FORMATS:
            return JsonResponse(
                {"ok": False, "error": "Hanya gambar JPEG, PNG atau WEBP diperbolehkan."}, status=400
            )

        img = ImageOps.exif_transpose(img) # fix phone rotation
        img = _flatten_to_rgb(img)
        img = ImageOps.fit(img, (AVATAR_SIZE, AVATAR_SIZE), Image.LANCZOS) # center-crop square
    except Exception:
        return JsonResponse({"ok": False, "error": "Gambar invalid atau rusak."}, status=400)

    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=85, optimize=True)

    user = request.user
    old_name = user.pfp.name if user.pfp else None

    user.pfp.save(
        f"user_{user.pk}_{uuid.uuid4().hex[:8]}.jpg",
        ContentFile(buffer.getvalue()),
        save=True,
    )
    if old_name and old_name != DEFAULT_PFP: # never delete the shared default
        user.pfp.storage.delete(old_name)

    url = f"{user.pfp.url}?v={int(timezone.now().timestamp())}" # cache-bust
    return JsonResponse({"ok": True, "url": url, "message": "Foto profil berhasil diubah."})


@login_required
@require_POST
def change_password(request):
    old = request.POST.get("old_password", "")
    new1 = request.POST.get("new_password1", "")
    new2 = request.POST.get("new_password2", "")

    if not request.user.check_password(old):
        return JsonResponse({"ok": False, "errors": ["Current password is incorrect."]}, status=400)
    if new1 != new2:
        return JsonResponse({"ok": False, "errors": ["New passwords do not match."]}, status=400)
    if new1 == old:
        return JsonResponse(
            {"ok": False, "errors": ["Password baru harus berbeda dengan password lama."]},
            status=400,
        )

    try:
        validate_password(new1, user=request.user)
    except ValidationError as e:
        return JsonResponse({"ok": False, "errors": list(e.messages)}, status=400)

    request.user.set_password(new1)
    request.user.save(update_fields=["password"])
    update_session_auth_hash(request, request.user)   # keeps the user logged in
    return JsonResponse({"ok": True, "message": "Password berhasil diubah."})