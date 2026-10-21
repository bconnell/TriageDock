"""Authentication and incident API endpoints."""
import hashlib
import json
import secrets
from django.core.cache import cache
from django.core.cache.backends.base import InvalidCacheBackendError

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

from .models import Incident, IncidentEvent
from .permissions import IsIncidentOperator
from .serializers import IncomingAlertSerializer, IncidentDetailSerializer, IncidentSerializer
from .services import InvalidTransition, ingest_alert, transition_incident


@ensure_csrf_cookie
@require_GET
def session_view(request):
    return JsonResponse({
        "authenticated": request.user.is_authenticated,
        "username": request.user.get_username() if request.user.is_authenticated else None,
    })


def _login_limit_key(request, username):
    source = request.META.get("REMOTE_ADDR", "unknown")[:128]
    identity = hashlib.sha256(f"{source}:{username.casefold()}".encode()).hexdigest()
    return f"triagedock:login:{identity}"


def _too_many_logins(key):
    # Redis increment is atomic. Treat cache outages as an error, not a bypass.
    if cache.add(key, 1, timeout=900):
        return False
    return cache.incr(key) > 5


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
    if not isinstance(username, str) or not isinstance(password, str):
        return JsonResponse({"detail": "Invalid credentials"}, status=400)
    try:
        # Also prevent attackers from generating unlimited passwords for one username.
        if _too_many_logins(_login_limit_key(request, username)):
            response = JsonResponse({"detail": "Too many sign-in attempts. Try later."}, status=429)
            response["Retry-After"] = "900"
            return response
    except Exception:
        return JsonResponse({"detail": "Sign-in is temporarily unavailable"}, status=503)
    user = authenticate(request, username=username, password=password)
    if user is None:
        return JsonResponse({"detail": "Invalid username or password"}, status=401)
    login(request, user)
    cache.delete(_login_limit_key(request, username))
    return JsonResponse({"authenticated": True, "username": user.get_username()})


@csrf_protect
@require_POST
def logout_view(request):
    logout(request)
    return JsonResponse({"authenticated": False})


class IngestRateThrottle(SimpleRateThrottle):
    scope = "ingest"

    def get_cache_key(self, request, view):
        # Do not trust unconfigured proxy forwarding headers for rate limiting.
        addr = request.META.get("REMOTE_ADDR", "unknown")
        key_hash = hashlib.sha256(request.headers.get("X-TriageDock-Key", "").encode()).hexdigest()[:24]
        ident = hashlib.sha256(f"{addr}:{key_hash}".encode()).hexdigest()
        return self.cache_format % {"scope": self.scope, "ident": ident}


class AlertIngestView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [IngestRateThrottle]

    @csrf_exempt
    def post(self, request):
        supplied = request.headers.get("X-TriageDock-Key", "")
        if not settings.INGEST_API_KEY or not secrets.compare_digest(
            supplied, settings.INGEST_API_KEY
        ):
            return Response({"detail": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)
        serializer = IncomingAlertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
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
    serializer_class = __import__("incidents.serializers", fromlist=["EventSerializer"]).EventSerializer
    pagination_class = __import__("incidents.pagination", fromlist=["EventPagination"]).EventPagination

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
