from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ai", "0005_faq"),
    ]

    operations = [
        migrations.AddField(
            model_name="memory",
            name="last_accessed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="responsecache",
            name="ttl_seconds",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="responsecache",
            name="is_web_result",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="resumeanalysis",
            name="found_skills",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="resumeanalysis",
            name="detected_sections",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="resumeanalysis",
            name="missing_sections",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="resumeanalysis",
            name="skills_score",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="resumeanalysis",
            name="sections_score",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="resumeanalysis",
            name="score_explanation",
            field=models.TextField(blank=True, default=""),
        ),
    ]
