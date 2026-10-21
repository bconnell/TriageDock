import uuid

from django.db import migrations, models


def populate_payload(apps, schema_editor):
    Delivery = apps.get_model("incidents", "NotificationDelivery")
    for row in Delivery.objects.filter(payload={} ).select_related("event__incident").iterator():
        event = row.event
        incident = event.incident
        row.payload = {
            "event_id": event.pk, "kind": event.kind,
            "incident_id": str(incident.pk), "title": incident.title,
            "severity": incident.severity, "status": incident.status,
        }
        row.save(update_fields=["payload"])


class Migration(migrations.Migration):
    dependencies = [("incidents", "0001_initial")]
    operations = [
        migrations.AddField(model_name="notificationdelivery", name="payload", field=models.JSONField(default=dict)),
        migrations.AddField(model_name="notificationdelivery", name="claim_token", field=models.UUIDField(null=True, blank=True)),
        migrations.AddField(model_name="notificationdelivery", name="claim_expires_at", field=models.DateTimeField(null=True, blank=True)),
        migrations.AlterField(
            model_name="notificationdelivery", name="status",
            field=models.CharField(
                max_length=10, default="pending",
                choices=[("pending", "Pending"), ("processing", "Processing"), ("sent", "Sent"), ("failed", "Failed")],
            ),
        ),
        migrations.RunPython(populate_payload, migrations.RunPython.noop),
    ]
