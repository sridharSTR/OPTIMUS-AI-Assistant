from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("ai", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="message",
            name="entities",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="message",
            name="intent",
            field=models.CharField(blank=True, default="", max_length=40),
        ),
        migrations.AddField(
            model_name="message",
            name="sentiment",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
        migrations.AddField(
            model_name="message",
            name="sentiment_score",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="Memory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(max_length=80)),
                ("value", models.TextField()),
                ("importance", models.PositiveSmallIntegerField(default=3)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="memories", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={
                "verbose_name_plural": "memories",
                "ordering": ["-importance", "-created_at"],
                "unique_together": {("user", "key", "value")},
            },
        ),
        migrations.CreateModel(
            name="ResumeAnalysis",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("filename", models.CharField(max_length=255)),
                ("extracted_text", models.TextField(blank=True)),
                ("skills", models.JSONField(blank=True, default=list)),
                ("education", models.JSONField(blank=True, default=list)),
                ("projects", models.JSONField(blank=True, default=list)),
                ("experience", models.JSONField(blank=True, default=list)),
                ("missing_skills", models.JSONField(blank=True, default=list)),
                ("suggestions", models.JSONField(blank=True, default=list)),
                ("interview_questions", models.JSONField(blank=True, default=list)),
                ("score", models.PositiveSmallIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="resume_analyses", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={
                "verbose_name_plural": "resume analyses",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="NLPEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("intent", models.CharField(max_length=40)),
                ("sentiment", models.CharField(max_length=20)),
                ("sentiment_score", models.FloatField(default=0)),
                ("entities", models.JSONField(blank=True, default=dict)),
                ("search_triggered", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "message",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="nlp_events", to="ai.message"),
                ),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="nlp_events", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
