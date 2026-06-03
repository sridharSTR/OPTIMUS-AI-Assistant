from django.db import migrations, models


def copy_existing_document_files(apps, schema_editor):
    Document = apps.get_model("ai", "Document")
    for document in Document.objects.exclude(file=""):
        if document.file_data:
            continue
        try:
            with document.file.open("rb") as handle:
                document.file_data = handle.read()
            document.save(update_fields=["file_data"])
            document.file.delete(save=False)
        except (FileNotFoundError, OSError, ValueError):
            continue


class Migration(migrations.Migration):

    dependencies = [
        ("ai", "0009_memory_updated_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="file_data",
            field=models.BinaryField(default=b"", help_text="Original uploaded document bytes stored in PostgreSQL"),
            preserve_default=False,
        ),
        migrations.RunPython(copy_existing_document_files, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="document",
            name="file",
        ),
    ]
