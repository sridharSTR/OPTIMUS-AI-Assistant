from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):

    dependencies = [
        ("ai", "0008_alter_nlpevent_options_memory_confidence_score_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="memory",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, default=timezone.now),
            preserve_default=False,
        ),
    ]
