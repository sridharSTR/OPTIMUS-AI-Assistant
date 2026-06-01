from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="EmailOTP",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("username", models.CharField(max_length=150)),
                ("email", models.EmailField(max_length=254, unique=True)),
                ("display_name", models.CharField(blank=True, max_length=120)),
                ("password_hash", models.CharField(max_length=128)),
                ("code_hash", models.CharField(max_length=128)),
                ("attempts", models.PositiveSmallIntegerField(default=0)),
                ("expires_at", models.DateTimeField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "email OTP",
                "verbose_name_plural": "email OTPs",
            },
        ),
    ]
