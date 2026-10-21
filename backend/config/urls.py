from django.contrib import admin
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
from incidents.tasks import WORKER_HEARTBEAT_KEY
from django.urls import include, path
from django.views.generic import TemplateView

from incidents import views

def readiness(request):
    checks = {"postgresql": False, "redis": False, "worker": False}
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            checks["postgresql"] = cursor.fetchone()[0] == 1
    except Exception:
        pass
    try:
        cache.set("triagedock:ready:test", "ok", timeout=10)
        checks["redis"] = cache.get("triagedock:ready:test") == "ok"
        checks["worker"] = bool(cache.get(WORKER_HEARTBEAT_KEY))
    except Exception:
        pass
    return JsonResponse({"ready": all(checks.values()), "checks": checks},
                        status=200 if all(checks.values()) else 503)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/session/", views.session_view, name="session"),
    path("api/v1/login/", views.login_view, name="login"),
    path("api/v1/logout/", views.logout_view, name="logout"),
    path("api/v1/", include("incidents.urls")),
    path("health/", lambda request: JsonResponse({"status": "ok"})),
    path("ready/", readiness, name="readiness"),
    path("", TemplateView.as_view(template_name="ui/index.html"), name="dashboard"),
]
