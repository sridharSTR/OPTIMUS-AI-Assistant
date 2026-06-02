from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """
    Extended User model for OPTIMUS AI chatbot.
    Supports authentication, role-based access control, and email verification.
    
    Fields optimized for:
    - Fast authentication lookups (email_verified indexed)
    - Role-based access control queries (role indexed)
    - User activity tracking (last_login)
    - Admin filtering (is_banned indexed)
    """
    class Role(models.TextChoices):
        USER = "user", "User"
        MODERATOR = "moderator", "Moderator"
        ADMIN = "admin", "Admin"
        SUPER_ADMIN = "super_admin", "Super Admin"

    PRIMARY_SUPER_ADMIN_EMAIL = "sivasridhar2502@gmail.com"

    display_name = models.CharField(max_length=120, blank=True)
    email_verified = models.BooleanField(default=False, db_index=True)  # Index for auth queries
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.USER, db_index=True)  # Index for role filtering
    is_banned = models.BooleanField(default=False, db_index=True)  # Index for user filtering
    last_login_at = models.DateTimeField(null=True, blank=True)  # Track actual logins vs Django's last_login

    def save(self, *args, **kwargs):
        """Auto-promote super admin and ensure role consistency."""
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
    """
    Email OTP verification for register and login flows.
    
    Security features:
    - Hashed OTP storage (never store plaintext)
    - Expiry enforcement
    - Attempt limiting
    - Purpose tracking (register vs login)
    
    Cleanup: Run `python manage.py purge_expired_otp` to remove old records.
    """
    class Purpose(models.TextChoices):
        REGISTER = "register", "Register"
        LOGIN = "login", "Login"

    username = models.CharField(max_length=150)
    email = models.EmailField(db_index=True)  # Fast lookup for OTP verification
    display_name = models.CharField(max_length=120, blank=True)
    password_hash = models.CharField(max_length=128, blank=True, default="")
    code_hash = models.CharField(max_length=128)
    purpose = models.CharField(max_length=20, choices=Purpose.choices, default=Purpose.REGISTER, db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    expires_at = models.DateTimeField(db_index=True)  # Index for cleanup queries
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "email OTP"
        verbose_name_plural = "email OTPs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email", "purpose"], name="otp_email_purpose_idx"),  # Find latest OTP for email
            models.Index(fields=["expires_at"], name="otp_expires_idx"),  # Cleanup queries
        ]

    def __str__(self):
        return f"{self.email} verification"

    @property
    def is_expired(self):
        """Check if OTP has passed expiration time."""
        return timezone.now() >= self.expires_at


class AdminRegistrationRequest(models.Model):
    """
    Admin role promotion workflow.
    
    Workflow:
    1. Non-admin user requests admin access
    2. Super admin reviews and approves/rejects
    3. System updates user.role and status
    
    Optimized for:
    - Quick pending request queries (status indexed)
    - Admin review workflow (reviewed_at indexed)
    """
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="admin_registration_request"
    )
    requested_role = models.CharField(
        max_length=20,
        choices=User.Role.choices,
        default=User.Role.ADMIN
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True  # Fast pending request queries
    )
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_admin_registration_requests",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["status", "-created_at"], name="admreq_status_created_idx"),  # Pending requests first
        ]

    def __str__(self):
        return f"{self.user.email} admin request ({self.status})"
