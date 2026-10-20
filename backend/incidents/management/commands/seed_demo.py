"""Create a few local sample incidents without duplicating seeds on repeated calls."""
from django.core.management.base import BaseCommand

from incidents.models import Incident
from incidents.services import ingest_alert

EXAMPLES = [
    {"source": "gateway-prod-01", "external_key": "latency-p99",
     "title": "Elevated gateway latency", "description": "P99 response latency above 1200ms for five minutes.", "severity": "critical"},
    {"source": "database-cluster", "external_key": "replica-delay",
     "title": "Replication lag detected", "description": "Read replica is 14 seconds behind primary.", "severity": "high"},
    {"source": "billing-worker", "external_key": "queue-depth",
     "title": "Processing queue growing", "description": "Pending billing jobs exceed threshold.", "severity": "medium"},
    {"source": "cdn-edge", "external_key": "cache-hit",
     "title": "Cache hit ratio below target", "description": "Regional cache hit ratio has dropped.", "severity": "low"},
]


class Command(BaseCommand):
    help = "Create safe, clearly labeled demo incidents for local development"

    def handle(self, *args, **options):
        for example in EXAMPLES:
            if not Incident.objects.filter(
                source=example["source"], external_key=example["external_key"]
            ).exists():
                ingest_alert(example)
        self.stdout.write(self.style.SUCCESS("Demo data is ready (idempotent)."))
