from rest_framework import serializers

from .models import Incident, IncidentEvent, NotificationDelivery


class IncomingAlertSerializer(serializers.Serializer):
    source = serializers.CharField(max_length=80, trim_whitespace=True)
    external_key = serializers.CharField(max_length=160, trim_whitespace=True)
    title = serializers.CharField(max_length=200, trim_whitespace=True)
    description = serializers.CharField(max_length=4000, required=False, allow_blank=True)
    severity = serializers.ChoiceField(choices=Incident.Severity.choices)

    def validate_source(self, value):
        if not value:
            raise serializers.ValidationError("Source is required")
        return value


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = IncidentEvent
        fields = ["id", "kind", "actor", "created_at"]


class DeliverySerializer(serializers.ModelSerializer):
    event_kind = serializers.CharField(source="event.kind", read_only=True)

    class Meta:
        model = NotificationDelivery
        fields = ["id", "event_kind", "status", "attempts", "last_error", "sent_at"]


class IncidentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Incident
        fields = [
            "id", "source", "external_key", "title", "description",
            "severity", "status", "occurrences", "first_seen_at",
            "last_seen_at", "acknowledged_at", "resolved_at",
        ]


class IncidentDetailSerializer(IncidentSerializer):
    events = serializers.SerializerMethodField()
    events_has_more = serializers.SerializerMethodField()
    deliveries = serializers.SerializerMethodField()

    class Meta(IncidentSerializer.Meta):
        fields = IncidentSerializer.Meta.fields + ["events", "events_has_more", "deliveries"]

    def get_events(self, obj):
        # Bound detail payload; full history remains available as paginated API.
        rows = list(obj.events.order_by("-created_at", "-pk")[:51])
        return EventSerializer(list(reversed(rows[:50])), many=True).data

    def get_events_has_more(self, obj):
        return obj.events.count() > 50

    def get_deliveries(self, obj):
        deliveries = NotificationDelivery.objects.filter(event__incident=obj).select_related("event")
        return DeliverySerializer(deliveries, many=True).data
