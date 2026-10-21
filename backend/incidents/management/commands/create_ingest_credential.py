import hashlib
import secrets

from django.core.management.base import BaseCommand, CommandError
from incidents.models import IngestCredential


class Command(BaseCommand):
    help = "Generate a one-time ingestion key scoped to one alert source."

    def add_arguments(self, parser):
        parser.add_argument("--label", required=True)
        parser.add_argument("--source", required=True)

    def handle(self, *args, **opts):
        label, source = opts["label"].strip(), opts["source"].strip()
        if not label or not source or len(label) > 80 or len(source) > 80:
            raise CommandError("Both label and source must be 1-80 characters")
        if IngestCredential.objects.filter(label=label).exists():
            raise CommandError("Credential label already exists. Rotate by creating a new label, then revoking the previous label.")
        key = secrets.token_urlsafe(48)
        IngestCredential.objects.create(
            label=label, source=source, key_digest=hashlib.sha256(key.encode()).hexdigest()
        )
        self.stdout.write("Store this secret securely. It will not be shown again:")
        self.stdout.write(key)
