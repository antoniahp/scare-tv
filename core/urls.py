"""Routes: the admin, the night log API (DRF) and the web mirror demo at the root."""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import RedirectView
from django.views.static import serve

urlpatterns = [
    path("admin", RedirectView.as_view(url="/admin/")),     # the catch-all below would otherwise swallow it
    path("admin/", admin.site.urls),
    path("api/", include("infrastructure.api.urls")),
    re_path(r"^(?P<path>.*)$", lambda request, path: serve(request, path or "index.html", document_root=settings.SCARE_TV["WEB_DIR"])),
]
