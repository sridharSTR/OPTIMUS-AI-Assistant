from django.contrib.auth.hashers import check_password
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import AdminRegistrationRequest, EmailOTP, User
from .utils import create_and_send_otp

ADMIN_ROLES = {User.Role.SUPER_ADMIN, User.Role.ADMIN, User.Role.MODERATOR}
ADMIN_ONLY_MESSAGE = "You are not an admin. Admin only access is allowed on this page. Please use User Login or ask the super admin to promote your account."


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "display_name", "email_verified", "role", "is_banned")
        read_only_fields = ("id", "email", "email_verified", "role", "is_banned")


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, required=False, allow_blank=True)
    full_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    email = serializers.EmailField()
    display_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8, required=False)
    access_role = serializers.ChoiceField(choices=("user", "admin"), required=False, write_only=True)

    def validate_email(self, value):
        email = value.lower()
        access_role = (getattr(self, "initial_data", {}) or {}).get("access_role")
        existing_user = User.objects.filter(email__iexact=email, email_verified=True).first()
        if existing_user and not (access_role == "admin" and existing_user.role not in ADMIN_ROLES):
            raise serializers.ValidationError("A user with this email already exists.")
        return email

    def validate_username(self, value):
        if not value:
            return value
        if User.objects.filter(username__iexact=value, email_verified=True).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value

    def validate(self, attrs):
        if attrs.get("confirm_password") is not None and attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        email = attrs["email"].lower()
        if attrs.get("access_role") == "admin" and email != User.PRIMARY_SUPER_ADMIN_EMAIL:
            existing_user = User.objects.filter(email__iexact=email).first()
            if existing_user and existing_user.role in ADMIN_ROLES:
                raise serializers.ValidationError({"email": "This email already has admin access. Please use Admin Login."})
            if existing_user and existing_user.email_verified and not existing_user.check_password(attrs["password"]):
                raise serializers.ValidationError({"password": "Enter your current account password to request admin access."})
        default_username = self._available_username(email.split("@")[0])
        attrs["username"] = attrs.get("username") or default_username
        attrs["display_name"] = attrs.get("full_name") or attrs.get("display_name") or attrs["username"]
        existing_user = User.objects.filter(email__iexact=attrs["email"]).first()
        username_owner = User.objects.filter(username__iexact=attrs["username"]).first()
        if username_owner and username_owner != existing_user:
            raise serializers.ValidationError("This username is already used by another account.")
        return attrs

    def _available_username(self, base):
        candidate = base[:150] or "user"
        suffix = 1
        while User.objects.filter(username__iexact=candidate).exists():
            suffix += 1
            trimmed = base[: max(1, 150 - len(str(suffix)) - 1)]
            candidate = f"{trimmed}-{suffix}"
        return candidate

    def create(self, validated_data):
        user = User.objects.filter(email__iexact=validated_data["email"]).first()
        if (
            validated_data.get("access_role") == "admin"
            and user
            and user.email_verified
            and user.email.lower() != User.PRIMARY_SUPER_ADMIN_EMAIL
        ):
            AdminRegistrationRequest.objects.update_or_create(
                user=user,
                defaults={
                    "requested_role": User.Role.ADMIN,
                    "status": AdminRegistrationRequest.Status.PENDING,
                    "reviewed_by": None,
                    "reviewed_at": None,
                },
            )
            self.context["pending_admin_request"] = True
            self.context["admin_request_message"] = (
                "Admin registration request sent. An existing admin can approve it from the admin panel."
            )
            return user

        if user is None:
            user = User(
                username=validated_data["username"],
                email=validated_data["email"],
                display_name=validated_data.get("display_name", ""),
                is_active=False,
                email_verified=False,
            )
        else:
            user.username = validated_data["username"]
            user.display_name = validated_data.get("display_name", "")
            user.is_active = False
            user.email_verified = False

        if validated_data["email"].lower() != User.PRIMARY_SUPER_ADMIN_EMAIL:
            user.role = User.Role.USER
            user.is_staff = False
            user.is_superuser = False

        user.set_password(validated_data["password"])
        user.save()

        if validated_data.get("access_role") == "admin" and user.email.lower() != User.PRIMARY_SUPER_ADMIN_EMAIL:
            AdminRegistrationRequest.objects.update_or_create(
                user=user,
                defaults={
                    "requested_role": User.Role.ADMIN,
                    "status": AdminRegistrationRequest.Status.PENDING,
                    "reviewed_by": None,
                    "reviewed_at": None,
                },
            )

        code, message = create_and_send_otp(user, EmailOTP.Purpose.REGISTER)
        self.context["otp_code"] = code
        self.context["otp_message"] = message
        return user


class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(min_length=6, max_length=6)

    def validate(self, attrs):
        email = attrs["email"].lower()
        otp = EmailOTP.objects.filter(email__iexact=email).order_by("-created_at").first()
        if otp is None:
            raise serializers.ValidationError("No pending verification was found for this email.")
        EmailOTP.objects.filter(email__iexact=email).exclude(pk=otp.pk).delete()

        if otp.is_expired:
            otp.delete()
            raise serializers.ValidationError("This OTP has expired. Please register again.")

        if otp.attempts >= 5:
            otp.delete()
            raise serializers.ValidationError("Too many invalid attempts. Please register again.")

        if not check_password(attrs["otp"], otp.code_hash):
            otp.attempts += 1
            otp.save(update_fields=["attempts"])
            raise serializers.ValidationError("Invalid OTP code.")

        try:
            user = User.objects.get(email__iexact=otp.email)
        except User.DoesNotExist as exc:
            otp.delete()
            raise serializers.ValidationError("No user was found for this OTP.") from exc

        if user.email.lower() != otp.email.lower():
            otp.delete()
            raise serializers.ValidationError("This OTP does not match the account email.")

        update_fields = []
        if otp.purpose == EmailOTP.Purpose.REGISTER:
            user.is_active = True
            user.email_verified = True
            user.display_name = otp.display_name
            update_fields = ["is_active", "email_verified", "display_name"]
        elif otp.purpose == EmailOTP.Purpose.LOGIN:
            if not user.is_active or not user.email_verified:
                otp.delete()
                raise serializers.ValidationError("Please verify your registration before logging in.")
            user.last_login_at = timezone.now()
            update_fields = ["last_login_at"]

        if update_fields:
            user.save(update_fields=update_fields)
        otp.delete()

        if otp.purpose == EmailOTP.Purpose.REGISTER:
            return {
                "user": UserSerializer(user).data,
                "purpose": EmailOTP.Purpose.REGISTER,
                "registration_verified": True,
                "detail": "Registration Successful. Your account has been verified successfully.",
            }

        refresh = RefreshToken.for_user(user)
        return {
            "user": UserSerializer(user).data,
            "purpose": EmailOTP.Purpose.LOGIN,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }


class LoginSerializer(serializers.Serializer):
    email = serializers.CharField(required=False, allow_blank=True)
    username = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)
    access_role = serializers.ChoiceField(choices=("user", "admin"), required=False, write_only=True)

    def validate(self, attrs):
        login_value = (attrs.get("email") or attrs.get("username") or "").strip()
        if not login_value:
            raise serializers.ValidationError({"email": "Email is required."})

        user = (
            User.objects.filter(email__iexact=login_value).first()
            or User.objects.filter(username__iexact=login_value).first()
        )
        if not user or not user.check_password(attrs["password"]):
            raise serializers.ValidationError("Invalid email or password.")
        if user.email.lower() == User.PRIMARY_SUPER_ADMIN_EMAIL:
            user.save()
        if user.is_banned:
            raise serializers.ValidationError("This account has been banned. Contact the administrator.")
        if not user.email_verified or not user.is_active:
            raise serializers.ValidationError("Please verify your registration OTP before logging in.")
        if attrs.get("access_role") == "admin" and user.role not in ADMIN_ROLES:
            raise serializers.ValidationError(ADMIN_ONLY_MESSAGE)

        code, message = create_and_send_otp(user, EmailOTP.Purpose.LOGIN)
        self.context["otp_code"] = code
        self.context["otp_message"] = message
        return {
            "requires_otp": True,
            "email": user.email,
            "detail": message,
        }
