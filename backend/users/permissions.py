from rest_framework.permissions import BasePermission


class IsEmailVerified(BasePermission):
    message = "Please verify your email OTP before accessing this page."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return True
        return bool(user.is_active and getattr(user, "email_verified", False))
