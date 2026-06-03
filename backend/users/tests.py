from django.conf import settings
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from .models import AdminRegistrationRequest, EmailOTP, User


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    SHOW_DEV_OTP=True,
    JWT_COOKIE_SECURE=False,
)
class AuthOTPTests(APITestCase):
    def test_register_verifies_without_session_cookies(self):
        register_response = self.client.post(
            reverse("register"),
            {
                "full_name": "Test User",
                "email": "test@example.com",
                "password": "strong-pass-123",
                "confirm_password": "strong-pass-123",
                "access_role": "user",
            },
            format="json",
        )

        self.assertEqual(register_response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(register_response.data["requires_otp"])

        verify_response = self.client.post(
            reverse("verify_otp"),
            {
                "email": "test@example.com",
                "otp": register_response.data["dev_otp"],
            },
            format="json",
        )

        self.assertEqual(verify_response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn("access", verify_response.data)
        self.assertNotIn("refresh", verify_response.data)
        self.assertEqual(verify_response.data["purpose"], EmailOTP.Purpose.REGISTER)
        self.assertTrue(verify_response.data["registration_verified"])
        self.assertEqual(
            verify_response.data["detail"],
            "Registration Successful. Your account has been verified successfully.",
        )
        self.assertEqual(verify_response.data["user"]["email"], "test@example.com")
        self.assertNotIn(settings.JWT_AUTH_COOKIE, verify_response.cookies)
        self.assertNotIn(settings.JWT_REFRESH_COOKIE, verify_response.cookies)

    def test_new_admin_registration_sends_otp_and_creates_pending_request(self):
        register_response = self.client.post(
            reverse("register"),
            {
                "full_name": "Admin Candidate",
                "email": "admin-candidate@example.com",
                "password": "strong-pass-123",
                "confirm_password": "strong-pass-123",
                "access_role": "admin",
            },
            format="json",
        )

        self.assertEqual(register_response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(register_response.data["requires_otp"])
        self.assertIn("dev_otp", register_response.data)

        user = User.objects.get(email__iexact="admin-candidate@example.com")
        self.assertFalse(user.is_active)
        self.assertFalse(user.email_verified)
        self.assertEqual(user.role, User.Role.USER)
        self.assertTrue(
            AdminRegistrationRequest.objects.filter(
                user=user,
                status=AdminRegistrationRequest.Status.PENDING,
            ).exists()
        )

        verify_response = self.client.post(
            reverse("verify_otp"),
            {
                "email": "admin-candidate@example.com",
                "otp": register_response.data["dev_otp"],
            },
            format="json",
        )

        self.assertEqual(verify_response.status_code, status.HTTP_201_CREATED)
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertTrue(user.email_verified)
        self.assertEqual(user.role, User.Role.USER)
        self.assertNotIn(settings.JWT_AUTH_COOKIE, verify_response.cookies)
        self.assertNotIn(settings.JWT_REFRESH_COOKIE, verify_response.cookies)

    def test_new_login_otp_replaces_duplicate_pending_otps(self):
        user = User.objects.create_user(
            username="login-user",
            email="login@example.com",
            password="strong-pass-123",
            is_active=True,
            email_verified=True,
        )
        EmailOTP.objects.create(
            username=user.username,
            email=user.email,
            display_name=user.display_name,
            password_hash=user.password,
            code_hash="old-code",
            purpose=EmailOTP.Purpose.LOGIN,
            expires_at=timezone.now() + timezone.timedelta(minutes=10),
        )
        EmailOTP.objects.create(
            username=user.username,
            email=user.email.upper(),
            display_name=user.display_name,
            password_hash=user.password,
            code_hash="older-code",
            purpose=EmailOTP.Purpose.LOGIN,
            expires_at=timezone.now() + timezone.timedelta(minutes=10),
        )

        login_response = self.client.post(
            reverse("login"),
            {
                "email": "login@example.com",
                "password": "strong-pass-123",
                "access_role": "user",
            },
            format="json",
        )

        self.assertEqual(login_response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(EmailOTP.objects.filter(email__iexact=user.email).count(), 1)

        verify_response = self.client.post(
            reverse("verify_otp"),
            {
                "email": "login@example.com",
                "otp": login_response.data["dev_otp"],
            },
            format="json",
        )

        self.assertEqual(verify_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(verify_response.data["purpose"], EmailOTP.Purpose.LOGIN)
        self.assertEqual(verify_response.data["user"]["email"], "login@example.com")
        self.assertIn(settings.JWT_AUTH_COOKIE, verify_response.cookies)
        self.assertIn(settings.JWT_REFRESH_COOKIE, verify_response.cookies)

    def test_unverified_user_cannot_request_login_otp(self):
        User.objects.create_user(
            username="pending-user",
            email="pending@example.com",
            password="strong-pass-123",
            is_active=False,
            email_verified=False,
        )

        response = self.client.post(
            reverse("login"),
            {
                "email": "pending@example.com",
                "password": "strong-pass-123",
                "access_role": "user",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(EmailOTP.objects.filter(email__iexact="pending@example.com", purpose=EmailOTP.Purpose.LOGIN).exists())

    def test_logout_clears_cookies_without_persisting_refresh_tokens(self):
        response = self.client.post(reverse("logout"), format="json")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.cookies[settings.JWT_AUTH_COOKIE]["max-age"], 0)
        self.assertEqual(response.cookies[settings.JWT_REFRESH_COOKIE]["max-age"], 0)

    def test_token_refresh_requires_refresh_cookie(self):
        response = self.client.post(reverse("token_refresh"), {"refresh": "body-token-is-ignored"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_refresh_uses_refresh_cookie(self):
        user = User.objects.create_user(
            username="refresh-user",
            email="refresh@example.com",
            password="strong-pass-123",
            is_active=True,
            email_verified=True,
        )
        self.client.cookies[settings.JWT_REFRESH_COOKIE] = str(RefreshToken.for_user(user))

        response = self.client.post(reverse("token_refresh"), format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["detail"], "Token refreshed.")
        self.assertNotIn("access", response.data)
        self.assertNotIn("refresh", response.data)
        self.assertIn(settings.JWT_AUTH_COOKIE, response.cookies)

    def test_existing_user_can_request_admin_without_losing_access(self):
        user = User.objects.create_user(
            username="normal-user",
            email="normal@example.com",
            password="strong-pass-123",
            is_active=True,
            email_verified=True,
        )

        response = self.client.post(
            reverse("register"),
            {
                "full_name": "Normal User",
                "email": "normal@example.com",
                "password": "strong-pass-123",
                "confirm_password": "strong-pass-123",
                "access_role": "admin",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertTrue(response.data["admin_request_pending"])
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertTrue(user.email_verified)
        self.assertEqual(user.role, User.Role.USER)
        self.assertTrue(AdminRegistrationRequest.objects.filter(user=user, status=AdminRegistrationRequest.Status.PENDING).exists())

    def test_existing_user_admin_request_requires_current_password(self):
        user = User.objects.create_user(
            username="password-user",
            email="password@example.com",
            password="strong-pass-123",
            is_active=True,
            email_verified=True,
        )

        response = self.client.post(
            reverse("register"),
            {
                "full_name": "Password User",
                "email": "password@example.com",
                "password": "wrong-pass-123",
                "confirm_password": "wrong-pass-123",
                "access_role": "admin",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(AdminRegistrationRequest.objects.filter(user=user).exists())
