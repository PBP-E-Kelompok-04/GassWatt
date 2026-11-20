import uuid
from io import BytesIO

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password as django_validate_password
from django.contrib.auth.validators import ASCIIUsernameValidator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.base import ContentFile
from django.db.models import Q
from PIL import Image, ImageOps
from rest_framework import serializers

User = get_user_model()

USERNAME_MIN, USERNAME_MAX = 3, 20
MAX_AVATAR_BYTES = 2 * 1024 * 1024
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
AVATAR_SIZE = 256
NON_FIELD = "__all__"


def _flatten_to_rgb(img):
    has_alpha = img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)
    if has_alpha:
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.getchannel("A"))
        return bg
    return img.convert("RGB")


# ---------- User ----------
class UserSerializer(serializers.ModelSerializer):
    pfp = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "username", "email", "pfp", "is_staff", "is_superuser")

    def get_pfp(self, obj):
        return obj.pfp.url if getattr(obj, "pfp", None) else None


# ---------- Login ----------
class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(error_messages={
        "required": "Username atau email dibutuhkan.", "blank": "Username atau email dibutuhkan."})
    password = serializers.CharField(trim_whitespace=False, error_messages={
        "required": "Password dibutuhkan.", "blank": "Password dibutuhkan."})

    def validate(self, attrs):
        identifier = attrs["identifier"].strip()
        match = User.objects.filter(
            Q(username__iexact=identifier) | Q(email__iexact=identifier)
        ).first()
        user = authenticate(
            self.context.get("request"),
            username=match.get_username() if match else "",
            password=attrs["password"],
        )
        if user is None:
            raise serializers.ValidationError({NON_FIELD: ["Username/email atau password invalid."]})
        attrs["user"] = user
        return attrs


# ---------- Register ----------
class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(error_messages={
        "required": "Username dibutuhkan.", "blank": "Username dibutuhkan."})
    email = serializers.CharField(error_messages={
        "required": "Email dibutuhkan.", "blank": "Email dibutuhkan."})
    password = serializers.CharField(trim_whitespace=False, error_messages={
        "required": "Password dibutuhkan.", "blank": "Password dibutuhkan."})
    confirm_password = serializers.CharField(trim_whitespace=False, required=False, allow_blank=True)

    def validate_username(self, value):
        value = value.strip()
        if "@" in value:
            raise serializers.ValidationError("Username tidak boleh mengandung '@'.")
        if len(value) < USERNAME_MIN:
            raise serializers.ValidationError(f"Username minimal {USERNAME_MIN} karakter.")
        try:
            User._meta.get_field("username").run_validators(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("Username sudah diambil.")
        return value

    def validate_email(self, value):
        value = value.strip().lower()
        try:
            User._meta.get_field("email").run_validators(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Email sudah terdaftar.")
        return value

    def validate(self, attrs):
        errors = {}
        password = attrs["password"]
        try:
            django_validate_password(password, user=User(
                username=attrs.get("username", ""), email=attrs.get("email", "")))
        except DjangoValidationError as exc:
            errors["password"] = list(exc.messages)
        if password != attrs.get("confirm_password", ""):
            errors["confirm_password"] = ["Password tidak sama."]
        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
        )


# ---------- Live field validation ----------
class ValidateFieldSerializer(serializers.Serializer):
    field = serializers.ChoiceField(
        choices=["username", "email", "password"],
        error_messages={"invalid_choice": "Field tidak dikenal."})
    value = serializers.CharField(allow_blank=True, trim_whitespace=False, required=False, default="")
    username = serializers.CharField(allow_blank=True, required=False, default="")
    email = serializers.CharField(allow_blank=True, required=False, default="")

    def validate(self, attrs):
        field, value = attrs["field"], attrs["value"]
        found = []

        if field == "username":
            value = value.strip()
            if not value:
                found = ["Username dibutuhkan."]
            elif "@" in value:
                found = ["Username tidak boleh mengandung '@'."]
            elif len(value) < USERNAME_MIN:
                found = [f"Username minimal {USERNAME_MIN} karakter."]
            else:
                try:
                    User._meta.get_field("username").run_validators(value)
                except DjangoValidationError as exc:
                    found = list(exc.messages)
                if not found and User.objects.filter(username__iexact=value).exists():
                    found = ["Username sudah diambil."]

        elif field == "email":
            value = value.strip().lower()
            if not value:
                found = ["Email dibutuhkan."]
            else:
                try:
                    User._meta.get_field("email").run_validators(value)
                except DjangoValidationError as exc:
                    found = list(exc.messages)
                if not found and User.objects.filter(email__iexact=value).exists():
                    found = ["Email sudah terdaftar."]

        else:  # password
            if not value:
                found = ["Password dibutuhkan."]
            else:
                try:
                    django_validate_password(value, user=User(
                        username=attrs["username"].strip(), email=attrs["email"].strip().lower()))
                except DjangoValidationError as exc:
                    found = list(exc.messages)

        attrs["found"] = found
        return attrs


# ---------- Update username ----------
class UpdateUsernameSerializer(serializers.Serializer):
    username = serializers.CharField(error_messages={
        "required": "Username dibutuhkan.", "blank": "Username dibutuhkan."})

    def validate_username(self, value):
        value = value.strip()
        if not (USERNAME_MIN <= len(value) <= USERNAME_MAX):
            raise serializers.ValidationError(
                f"Username harus berjumlah {USERNAME_MIN}-{USERNAME_MAX} karakter.")
        try:
            ASCIIUsernameValidator()(value)
        except DjangoValidationError:
            raise serializers.ValidationError("Hanya huruf, angka and @ . + - _ diperbolehkan.")
        me = self.context["request"].user
        if User.objects.filter(username__iexact=value).exclude(pk=me.pk).exists():
            raise serializers.ValidationError("Username sudah diambil.")
        return value


# ---------- Update avatar ----------
class UpdateAvatarSerializer(serializers.Serializer):
    pfp = serializers.FileField(error_messages={
        "required": "No file uploaded.", "empty": "No file uploaded."})

    def validate_pfp(self, file):
        if file.size > MAX_AVATAR_BYTES:
            raise serializers.ValidationError("Gambar maksimal 2 MB.")
        try:
            img = Image.open(file)
            img.verify()
            file.seek(0)
            img = Image.open(file)  # must reopen after verify()
            fmt = img.format
            if fmt not in ALLOWED_FORMATS:
                raise serializers.ValidationError("Hanya gambar JPEG, PNG atau WEBP diperbolehkan.")
            img = ImageOps.exif_transpose(img)
            img = _flatten_to_rgb(img)
            img = ImageOps.fit(img, (AVATAR_SIZE, AVATAR_SIZE), Image.LANCZOS)
        except serializers.ValidationError:
            raise
        except Exception:
            raise serializers.ValidationError("Gambar invalid atau rusak.")

        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=85, optimize=True)
        user = self.context["request"].user
        return ContentFile(buffer.getvalue(), name=f"user_{user.pk}_{uuid.uuid4().hex[:8]}.jpg")


# ---------- Change password ----------
class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(trim_whitespace=False)
    new_password1 = serializers.CharField(trim_whitespace=False)
    new_password2 = serializers.CharField(trim_whitespace=False)

    def validate(self, attrs):
        user = self.context["request"].user
        old, new1, new2 = attrs["old_password"], attrs["new_password1"], attrs["new_password2"]
        if not user.check_password(old):
            raise serializers.ValidationError({"old_password": ["Current password is incorrect."]})
        if new1 != new2:
            raise serializers.ValidationError({"new_password2": ["New passwords do not match."]})
        if new1 == old:
            raise serializers.ValidationError(
                {"new_password1": ["Password baru harus berbeda dengan password lama."]})
        try:
            django_validate_password(new1, user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"new_password1": list(exc.messages)})
        return attrs
