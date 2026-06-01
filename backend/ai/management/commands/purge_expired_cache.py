from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from ai.models import ResponseCache


class Command(BaseCommand):
    help = "Delete expired AI response cache entries."

    def handle(self, *args, **options):
        now = timezone.now()
        expired_ids = [
            cache.id
            for cache in ResponseCache.objects.exclude(ttl_seconds__isnull=True).only("id", "created_at", "ttl_seconds")
            if cache.created_at + timedelta(seconds=cache.ttl_seconds) <= now
        ]
        deleted, _ = ResponseCache.objects.filter(id__in=expired_ids).delete()
        self.stdout.write(self.style.SUCCESS(f"Purged {deleted} expired cache entries."))
