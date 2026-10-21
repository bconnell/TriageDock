from django.contrib import admin
from .models import Incident, IncidentEvent, NotificationDelivery


class AuditReadOnlyAdmin(admin.ModelAdmin):
    """Admin is observational. Changes go through audited API services."""
    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Incident)
class IncidentAdmin(AuditReadOnlyAdmin):
    list_display = ("title", "source", "severity", "status", "occurrences", "last_seen_at")
    list_filter = ("status", "severity")
    search_fields = ("title", "source", "external_key")


@admin.register(IncidentEvent)
class IncidentEventAdmin(AuditReadOnlyAdmin):
    list_display = ("incident", "kind", "actor", "created_at")


@admin.register(NotificationDelivery)
class NotificationDeliveryAdmin(AuditReadOnlyAdmin):
    list_display = ("event", "status", "attempts", "next_attempt_at", "sent_at")
