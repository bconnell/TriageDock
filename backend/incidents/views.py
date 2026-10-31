"""Authentication and incident API endpoints."""
import hashlib
import json
import secrets
from django.core.cache import cache
from django.core.exceptions import RequestDataTooBig

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt, csrf_protect, ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST
from rest_framework import generics, permissions, status
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Incident, IncidentEvent, IngestCredential
from .pagination import EventPagination
from .permissions import IsIncidentOperator
from .serializers import IncomingAlertSerializer, IncidentDetailSerializer, IncidentSerializer, EventSerializer
from .services import InvalidTransition, ingest_alert, transition_incident


@ensure_csrf_cookie
@require_GET
def session_view(request):
    return JsonResponse({
        "authenticated": request.user.is_authenticated,
        "username": request.user.get_username() if request.user.is_authenticated else None,
        "can_manage_incidents": (
            request.user.has_perm("incidents.change_incident")
            if request.user.is_authenticated else False
        ),
    })


def _login_limit_key(request, username):
    source = request.META.get("REMOTE_ADDR", "unknown")[:128]
    identity = hashlib.sha256(f"{source}:{username.casefold()}".encode()).hexdigest()
    return f"triagedock:login:{identity}"


def _login_failures(key):
    # Shared Redis cache is mandatory in the deployed application.
    # Read the number of FAILED attempts; successful logins do not spend quota.
    return int(cache.get(key, 0))


def _record_login_failure(key):
    # An atomic add or increment keeps a fixed 15-minute failure window.
    if not cache.add(key, 1, timeout=900):
        cache.incr(key)


@csrf_protect
@require_POST
def login_view(request):
    try:
        data = json.loads(request.body)
        if not isinstance(data, dict):
            raise ValueError("Expected object")
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"detail": "Invalid JSON object"}, status=400)
    username = data.get("username", "")
    password = data.get("password", "")
    if (not isinstance(username, str) or not isinstance(password, str)
            or not 1 <= len(username) <= 150 or len(password) > 1024):
        return JsonResponse({"detail": "Invalid credentials"}, status=400)
    user_key = _login_limit_key(request, username)
    address_key = _login_limit_key(request, "*")
    try:
        if (_login_failures(user_key) >= 5 or
                _login_failures(address_key) >= 5):
            response = JsonResponse({"detail": "Too many sign-in attempts. Try later."}, status=429)
            response["Retry-After"] = "900"
            return response
    except Exception:
        return JsonResponse({"detail": "Sign-in is temporarily unavailable"}, status=503)
    user = authenticate(request, username=username, password=password)
    if user is None:
        try:
            _record_login_failure(user_key)
            _record_login_failure(address_key)
        except Exception:
            # A cache outage must not permit an unlimited password-guessing path.
            return JsonResponse({"detail": "Sign-in is temporarily unavailable"}, status=503)
        return JsonResponse({"detail": "Invalid username or password"}, status=401)
    try:
        # A valid sign-in may clear this account's failures; the address-wide
        # budget is intentionally NOT cleared, preventing credential-stuffing bypass.
        cache.delete(user_key)
    except Exception:
        return JsonResponse({"detail": "Sign-in is temporarily unavailable"}, status=503)
    login(request, user)
    return JsonResponse({
        "authenticated": True,
        "username": user.get_username(),
        "can_manage_incidents": user.has_perm("incidents.change_incident"),
    })


@csrf_protect
@require_POST
def logout_view(request):
    logout(request)
    return JsonResponse({"authenticated": False, "can_manage_incidents": False})


class IngestRateThrottle(SimpleRateThrottle):
    scope = "ingest"

    def get_cache_key(self, request, view):
        # Do not trust unconfigured proxy forwarding headers for rate limiting.
        addr = request.META.get("REMOTE_ADDR", "unknown")
        # Include only REMOTE_ADDR: a different guessed key must not reset the quota.
        ident = hashlib.sha256(addr.encode()).hexdigest()
        return self.cache_format % {"scope": self.scope, "ident": ident}


class AlertIngestView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [IngestRateThrottle]

    @csrf_exempt
    def post(self, request):
        supplied = request.headers.get("X-TriageDock-Key", "")
        digest = hashlib.sha256(supplied.encode("utf-8")).hexdigest()
        credential = (IngestCredential.objects.filter(key_digest=digest, revoked_at__isnull=True)
                      .only("source").first() if supplied else None)
        shared_ok = bool(
            settings.INGEST_SHARED_KEY_ENABLED and settings.INGEST_API_KEY and
            secrets.compare_digest(supplied, settings.INGEST_API_KEY)
        )
        if credential is None and not shared_ok:
            return Response({"detail": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)
        # Access Django's guarded raw body BEFORE DRF streams JSON. This applies
        # DATA_UPLOAD_MAX_MEMORY_SIZE even on parsers that read request streams.
        try:
            _ = request._request.body
        except RequestDataTooBig:
            return Response({"detail": "Alert body too large"},
                            status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
        serializer = IncomingAlertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if credential is not None and credential.source != serializer.validated_data["source"]:
            return Response({"detail": "Key not authorized for this source"}, status=status.HTTP_403_FORBIDDEN)
        incident, created = ingest_alert(serializer.validated_data)
        return Response(
            IncidentSerializer(incident).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class IncidentListView(generics.ListAPIView):
    serializer_class = IncidentSerializer
    queryset = Incident.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset()
        for key, options in (
            ("status", Incident.Status.values),
            ("severity", Incident.Severity.values),
        ):
            value = self.request.query_params.get(key)
            if value:
                if value not in options:
                    from rest_framework.exceptions import ValidationError
                    raise ValidationError({key: "Unknown value"})
                queryset = queryset.filter(**{key: value})
        q = self.request.query_params.get("q", "").strip()[:120]
        if q:
            queryset = queryset.filter(
                Q(title__icontains=q) | Q(source__icontains=q) |
                Q(external_key__icontains=q)
            )
        return queryset


class IncidentDetailView(generics.RetrieveAPIView):
    serializer_class = IncidentDetailSerializer
    queryset = Incident.objects.all()


class IncidentActionView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsIncidentOperator]

    def post(self, request, pk, action):
        get_object_or_404(Incident, pk=pk)
        try:
            incident = transition_incident(pk, action, request.user.get_username())
        except InvalidTransition as exc:
            return Response({"detail": str(exc)}, status=409)
        return Response(IncidentDetailSerializer(incident).data)


class IncidentEventListView(generics.ListAPIView):
    serializer_class = EventSerializer
    pagination_class = EventPagination

    def get_queryset(self):
        get_object_or_404(Incident, pk=self.kwargs["pk"])
        return IncidentEvent.objects.filter(incident_id=self.kwargs["pk"]).order_by("-created_at", "-pk")


class StatisticsView(APIView):
    def get(self, request):
        counts = {item["status"]: item["count"] for item in (
            Incident.objects.values("status").annotate(count=Count("id"))
        )}
        return Response({
            "total": sum(counts.values()),
            "open": counts.get(Incident.Status.OPEN, 0),
            "acknowledged": counts.get(Incident.Status.ACKNOWLEDGED, 0),
            "resolved": counts.get(Incident.Status.RESOLVED, 0),
            "critical_active": Incident.objects.filter(
                severity=Incident.Severity.CRITICAL
            ).exclude(status=Incident.Status.RESOLVED).count(),
        })
