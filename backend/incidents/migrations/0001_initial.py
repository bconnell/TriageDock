# Initial schema for TriageDock. Matches incidents.models.
import uuid

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="Incident",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("fingerprint", models.CharField(editable=False, max_length=64, unique=True)),
                ("source", models.CharField(max_length=80)),
                ("external_key", models.CharField(max_length=160)),
                ("title", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True, max_length=4000)),
                ("severity", models.CharField(choices=[("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical")], max_length=8)),
                ("status", models.CharField(choices=[("open", "Open"), ("acknowledged", "Acknowledged"), ("resolved", "Resolved")], default="open", max_length=12)),
                ("occurrences", models.PositiveIntegerField(default=1)),
                ("first_seen_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("last_seen_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("acknowledged_at", models.DateTimeField(blank=True, null=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "ordering": ["-last_seen_at"],
                "indexes": [
                    models.Index(fields=["status", "-last_seen_at"], name="incident_status_recent"),
                    models.Index(fields=["severity", "-last_seen_at"], name="incident_severity_recent"),
                ],
            },
        ),
        migrations.CreateModel(
            name="IncidentEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[("created", "Created"), ("repeated", "Repeated"), ("reopened", "Reopened"), ("acknowledged", "Acknowledged"), ("resolved", "Resolved")], max_length=16)),
                ("actor", models.CharField(blank=True, default="", max_length=150)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("incident", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="events", to="incidents.incident")),
            ],
            options={"ordering": ["created_at", "id"]},
        ),
        migrations.CreateModel(
            name="NotificationDelivery",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("pending", "Pending"), ("sent", "Sent"), ("failed", "Failed")], default="pending", max_length=8)),
                ("attempts", models.PositiveSmallIntegerField(default=0)),
                ("next_attempt_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("last_error", models.CharField(blank=True, default="", max_length=300)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("event", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="delivery", to="incidents.incidentevent")),
            ],
            options={"indexes": [models.Index(fields=["status", "next_attempt_at"], name="delivery_due_idx")]},
        ),
    ]
