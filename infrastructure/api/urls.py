from django.urls import path

from infrastructure.api.night.view import FalseAlarmView, HealthView, NightScaresView, NightSummaryView
from infrastructure.api.web.view import VisitView, WebScareView, WebSummaryView

urlpatterns = [
    path("health", HealthView.as_view()),
    path("night/summary", NightSummaryView.as_view()),
    path("night/scares", NightScaresView.as_view()),
    path("night/false-alarm", FalseAlarmView.as_view()),
    path("web/visits", VisitView.as_view()),
    path("web/scares", WebScareView.as_view()),
    path("web/summary", WebSummaryView.as_view()),
]
