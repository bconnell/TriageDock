from django.contrib import admin

from .models import Incident, IncidentEvent, NotificationDelivery


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ("title", "source", "severity", "status", "occurrences", "last_seen_at")
    list_filter = ("status", "severity")
    search_fields = ("title", "source", "external_key")
    readonly_fields = ("fingerprint", "occurrences", "first_seen_at", "last_seen_at")
    def has_add_permission(self, request):
        return False


@admin.register(IncidentEvent)
class IncidentEventAdmin(admin.ModelAdmin):
    list_display = ("incident", "kind", "actor", "created_at")
    def has_add_permission(self, request):
        return False


@admin.register(NotificationDelivery)
class NotificationDeliveryAdmin(admin.ModelAdmin):
    list_display = ("event", "status", "attempts", "next_attempt_at", "sent_at")
    def has_add_permission(self, request):
        return False
