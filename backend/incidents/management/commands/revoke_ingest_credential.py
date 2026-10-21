from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from incidents.models import IngestCredential


class Command(BaseCommand):
    help = "Revoke one source-scoped API key without deleting its audit record."

    def add_arguments(self, parser):
        parser.add_argument("label")

    def handle(self, *args, **opts):
        changed = IngestCredential.objects.filter(
            label=opts["label"], revoked_at__isnull=True
        ).update(revoked_at=timezone.now())
        if changed != 1:
            raise CommandError("Active credential not found")
        self.stdout.write(self.style.SUCCESS("Credential revoked"))
