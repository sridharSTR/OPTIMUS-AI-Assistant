from django.db import migrations, models


PRIMARY_SUPER_ADMIN_EMAIL = "sivasridhar2502@gmail.com"


def assign_primary_super_admin(apps, schema_editor):
    User = apps.get_model("users", "User")
    User.objects.filter(email__iexact=PRIMARY_SUPER_ADMIN_EMAIL).update(
        role="super_admin",
        is_staff=True,
        is_superuser=True,
        is_active=True,
        is_banned=False,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0003_emailotp_purpose_user_email_verified_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[
                    ("user", "User"),
                    ("moderator", "Moderator"),
                    ("admin", "Admin"),
                    ("super_admin", "Super Admin"),
                ],
                default="user",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="is_banned",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(assign_primary_super_admin, migrations.RunPython.noop),
    ]
