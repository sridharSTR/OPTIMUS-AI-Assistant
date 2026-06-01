from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Verify SpaCy and the en_core_web_sm model are available."

    def handle(self, *args, **options):
        try:
            import spacy
        except ImportError:
            self.stdout.write(self.style.WARNING("SpaCy is not installed. Entity extraction will use regex-only fallback."))
            return

        try:
            spacy.load("en_core_web_sm")
        except OSError:
            self.stdout.write(self.style.WARNING("SpaCy model en_core_web_sm is missing. Entity extraction will use regex-only fallback."))
            return

        self.stdout.write(self.style.SUCCESS("SpaCy and en_core_web_sm are available."))
