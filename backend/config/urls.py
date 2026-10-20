from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from django.views.generic import TemplateView

from incidents import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/session/", views.session_view, name="session"),
    path("api/v1/login/", views.login_view, name="login"),
    path("api/v1/logout/", views.logout_view, name="logout"),
    path("api/v1/", include("incidents.urls")),
    path("health/", lambda request: JsonResponse({"status": "ok"})),
    path("", TemplateView.as_view(template_name="ui/index.html"), name="dashboard"),
]
