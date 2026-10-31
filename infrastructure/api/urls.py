from django.urls import path

from infrastructure.api.night.view import FalseAlarmView, HealthView, NightScaresView, NightSummaryView

urlpatterns = [
    path("health", HealthView.as_view()),
    path("night/summary", NightSummaryView.as_view()),
    path("night/scares", NightScaresView.as_view()),
    path("night/false-alarm", FalseAlarmView.as_view()),
]
