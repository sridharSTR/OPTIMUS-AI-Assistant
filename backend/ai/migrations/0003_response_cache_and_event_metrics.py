from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ai", "0002_nlp_memory_resume"),
    ]

    operations = [
        migrations.AddField(
            model_name="nlpevent",
            name="ai_called",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="nlpevent",
            name="cache_hit",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="nlpevent",
            name="handled_locally",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="nlpevent",
            name="route",
            field=models.CharField(blank=True, default="", max_length=40),
        ),
        migrations.CreateModel(
            name="ResponseCache",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("question_hash", models.CharField(max_length=64, unique=True)),
                ("normalized_question", models.TextField()),
                ("response", models.TextField()),
                ("intent", models.CharField(blank=True, default="general_chat", max_length=40)),
                ("hits", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["-updated_at"],
            },
        ),
    ]
