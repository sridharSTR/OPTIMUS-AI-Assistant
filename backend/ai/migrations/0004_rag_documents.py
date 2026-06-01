from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("ai", "0003_response_cache_and_event_metrics"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Document",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("filename", models.CharField(max_length=255)),
                ("file", models.FileField(upload_to="documents/%Y/%m/%d/")),
                ("file_type", models.CharField(choices=[("pdf", "PDF"), ("docx", "DOCX"), ("txt", "TXT")], max_length=10)),
                ("file_size", models.PositiveIntegerField()),
                ("extracted_text", models.TextField(blank=True)),
                ("processed", models.BooleanField(default=False)),
                ("processing_error", models.TextField(blank=True, default="")),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="documents", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={"ordering": ["-uploaded_at"]},
        ),
        migrations.CreateModel(
            name="DocumentChunk",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("chunk_index", models.PositiveIntegerField()),
                ("chunk_text", models.TextField()),
                ("page_number", models.PositiveIntegerField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "document",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="chunks", to="ai.document"),
                ),
            ],
            options={
                "ordering": ["document_id", "chunk_index"],
                "unique_together": {("document", "chunk_index")},
            },
        ),
        migrations.CreateModel(
            name="RAGQuery",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("message", models.TextField()),
                ("answer", models.TextField(blank=True)),
                ("sources", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "document",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="queries", to="ai.document"),
                ),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="rag_queries", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={
                "verbose_name_plural": "RAG queries",
                "ordering": ["-created_at"],
            },
        ),
    ]
