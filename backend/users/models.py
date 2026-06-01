from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    class Role(models.TextChoices):
        USER = "user", "User"
        MODERATOR = "moderator", "Moderator"
        ADMIN = "admin", "Admin"
        SUPER_ADMIN = "super_admin", "Super Admin"

    PRIMARY_SUPER_ADMIN_EMAIL = "sivasridhar2502@gmail.com"

    display_name = models.CharField(max_length=120, blank=True)
    email_verified = models.BooleanField(default=False)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.USER)
    is_banned = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.email and self.email.lower() == self.PRIMARY_SUPER_ADMIN_EMAIL:
            self.role = self.Role.SUPER_ADMIN
            self.is_staff = True
            self.is_superuser = True
            self.is_active = True
            self.is_banned = False
            update_fields = kwargs.get("update_fields")
            if update_fields is not None:
                kwargs["update_fields"] = set(update_fields) | {"role", "is_staff", "is_superuser", "is_active", "is_banned"}
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username


class EmailOTP(models.Model):
    class Purpose(models.TextChoices):
        REGISTER = "register", "Register"
        LOGIN = "login", "Login"

    username = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=120, blank=True)
    password_hash = models.CharField(max_length=128, blank=True, default="")
    code_hash = models.CharField(max_length=128)
    purpose = models.CharField(max_length=20, choices=Purpose.choices, default=Purpose.REGISTER)
    attempts = models.PositiveSmallIntegerField(default=0)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "email OTP"
        verbose_name_plural = "email OTPs"

    def __str__(self):
        return f"{self.email} verification"

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at


class AdminRegistrationRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="admin_registration_request")
    requested_role = models.CharField(max_length=20, choices=User.Role.choices, default=User.Role.ADMIN)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_admin_registration_requests",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.user.email} admin request ({self.status})"
