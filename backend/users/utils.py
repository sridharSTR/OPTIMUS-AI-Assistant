import random
from smtplib import SMTPException

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.mail import BadHeaderError, send_mail
from django.utils import timezone
from rest_framework import serializers

from .models import EmailOTP


def generate_otp_code():
    return f"{random.SystemRandom().randint(0, 999999):06d}"


def create_and_send_otp(user, purpose):
    code = generate_otp_code()
    EmailOTP.objects.update_or_create(
        email=user.email,
        defaults={
            "username": user.username,
            "display_name": user.display_name,
            "password_hash": user.password,
            "code_hash": make_password(code),
            "purpose": purpose,
            "attempts": 0,
            "expires_at": timezone.now() + settings.EMAIL_OTP_EXPIRY,
        },
    )

    try:
        expiry_minutes = int(settings.EMAIL_OTP_EXPIRY.total_seconds() // 60)
        display_name = user.display_name or user.username
        purpose_label = "login" if purpose == EmailOTP.Purpose.LOGIN else "account registration"
        greeting_line = (
            "Welcome back to OPTIMUS AI Assistant."
            if purpose == EmailOTP.Purpose.LOGIN
            else "Welcome to OPTIMUS AI Assistant."
        )
        send_mail(
            subject="OPTIMUS Security Verification Code",
            message=(
                f"Hello {display_name},\n\n"
                f"{greeting_line}\n\n"
                f"Your verification code is:\n\n{code}\n\n"
                f"Use this code to complete your {purpose_label}. This code will expire in {expiry_minutes} minutes.\n\n"
                "If you did not request this verification, please ignore this email.\n\n"
                "Best Regards,\nOPTIMUS Security Team\n\n"
                "Made by Sridhar M"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
            html_message=build_otp_email_html(display_name, code, expiry_minutes, purpose_label, greeting_line),
        )
    except (BadHeaderError, OSError, SMTPException) as exc:
        raise serializers.ValidationError(
            "Could not send OTP email. Please check SMTP settings and try again."
        ) from exc

    return code, "OTP sent to your email. Please verify to continue."


def build_otp_email_html(display_name, code, expiry_minutes, purpose_label, greeting_line):
    return f"""
<!doctype html>
<html>
  <body style="margin:0;background:#050814;font-family:Arial,Helvetica,sans-serif;color:#e5eefb;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:linear-gradient(135deg,#050814,#111827 52%,#082f49);padding:32px 12px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:560px;border:1px solid rgba(255,255,255,0.16);border-radius:18px;background:rgba(15,23,42,0.86);box-shadow:0 24px 70px rgba(8,47,73,0.38);overflow:hidden;">
            <tr>
              <td style="padding:28px 28px 18px;text-align:center;">
                <div style="display:inline-block;padding:10px 14px;border:1px solid rgba(103,232,249,0.35);border-radius:12px;background:rgba(34,211,238,0.12);color:#a5f3fc;font-weight:700;letter-spacing:0.08em;">OPTIMUS</div>
                <h1 style="margin:22px 0 8px;font-size:24px;line-height:1.25;color:#ffffff;">Security Verification Code</h1>
                <p style="margin:0;color:#cbd5e1;font-size:15px;line-height:1.6;">Hello {display_name}, {greeting_line}</p>
              </td>
            </tr>
            <tr>
              <td style="padding:8px 28px 24px;text-align:center;">
                <div style="margin:0 auto 18px;max-width:320px;border:1px solid rgba(103,232,249,0.32);border-radius:16px;background:rgba(255,255,255,0.08);padding:22px;">
                  <p style="margin:0 0 10px;color:#94a3b8;font-size:13px;text-transform:uppercase;letter-spacing:0.16em;">Verification Code</p>
                  <div style="font-size:36px;letter-spacing:0.26em;font-weight:800;color:#ffffff;">{code}</div>
                </div>
                <p style="margin:0 0 12px;color:#cbd5e1;font-size:15px;line-height:1.6;">Use this code to complete your <strong style="color:#ffffff;">{purpose_label}</strong>. It will expire in <strong style="color:#ffffff;">{expiry_minutes} minutes</strong>.</p>
                <p style="margin:0;color:#94a3b8;font-size:13px;line-height:1.6;">If you did not request this verification, please ignore this email. Never share this code with anyone.</p>
              </td>
            </tr>
            <tr>
              <td style="border-top:1px solid rgba(255,255,255,0.12);padding:18px 28px;text-align:center;color:#94a3b8;font-size:12px;">
                Best Regards,<br />
                <strong style="color:#cbd5e1;">OPTIMUS Security Team</strong><br />
                <span style="display:inline-block;margin-top:10px;color:#e2e8f0;font-weight:700;">Made by Sridhar M</span><br />
                <span style="color:#94a3b8;">Full-Stack Python Developer • React.js • Django • AI Applications</span>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""
