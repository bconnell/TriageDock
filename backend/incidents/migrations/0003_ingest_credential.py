from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [("incidents", "0002_delivery_claims")]
    operations = [
        migrations.CreateModel(name="IngestCredential", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("label", models.CharField(max_length=80, unique=True)),
            ("source", models.CharField(max_length=80)),
            ("key_digest", models.CharField(editable=False, max_length=64, unique=True)),
            ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
            ("revoked_at", models.DateTimeField(blank=True, null=True)),
        ]),
    ]
