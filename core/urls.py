"""Routes: the night log API (DRF) and the web mirror demo at the root."""

from django.conf import settings
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path("api/", include("infrastructure.api.urls")),
    re_path(r"^(?P<path>.*)$", lambda request, path: serve(request, path or "index.html", document_root=settings.SCARE_TV["WEB_DIR"])),
]
