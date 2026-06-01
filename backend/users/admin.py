from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import EmailOTP, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + ((("OPTIMUS Access"), {"fields": ("display_name", "email_verified", "role", "is_banned")}),)
    add_fieldsets = UserAdmin.add_fieldsets + ((("OPTIMUS Access"), {"fields": ("display_name", "email_verified", "role", "is_banned")}),)
    list_display = ("username", "email", "display_name", "role", "email_verified", "is_banned", "is_staff")
    list_filter = ("role", "email_verified", "is_banned", "is_staff", "is_superuser")
    search_fields = ("username", "email", "display_name")


@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display = ("email", "username", "purpose", "attempts", "expires_at", "created_at")
    search_fields = ("email", "username")
    readonly_fields = ("created_at",)
