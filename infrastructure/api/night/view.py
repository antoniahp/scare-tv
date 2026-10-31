"""The night log API (DRF). Numbers only: there is no image to serve."""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from application.commands.mark_false_alarm.command import MarkFalseAlarmCommand
from application.commands.mark_false_alarm.command_dto import MarkFalseAlarmCommandDTO
from application.queries.get_night_summary.query import GetNightSummaryQuery
from application.queries.get_night_summary.query_dto import GetNightSummaryQueryDTO
from application.queries.list_night_scares.query import ListNightScaresQuery
from application.queries.list_night_scares.query_dto import ListNightScaresQueryDTO
from domain.exceptions import NightNotFound, NothingToMark
from infrastructure import dependencies
from infrastructure.api.night.serializer import NightQuerySerializer, ScareEventSerializer


def _night_id(request, data=None):
    s = NightQuerySerializer(data=data if data is not None else request.query_params)
    s.is_valid(raise_exception=True)
    return s.validated_data.get("night")


class HealthView(APIView):
    def get(self, request):
        return Response({"ok": True})


class NightSummaryView(APIView):
    """GET /api/night/summary[?night=<uuid>] → the night summary (the latest one by default)."""

    def get(self, request):
        try:
            summary = GetNightSummaryQuery(dependencies.get_repositories()).execute(GetNightSummaryQueryDTO(night_id=_night_id(request)))
        except NightNotFound:
            return Response({"detail": "No nights yet. Start the TV with: make run"}, status=status.HTTP_404_NOT_FOUND)
        return Response(summary)


class NightScaresView(APIView):
    """GET /api/night/scares[?night=<uuid>] → every scare of the night, in order."""

    def get(self, request):
        try:
            scares = ListNightScaresQuery(dependencies.get_repositories()).execute(ListNightScaresQueryDTO(night_id=_night_id(request)))
        except NightNotFound:
            return Response([], status=status.HTTP_200_OK)
        return Response(ScareEventSerializer(scares, many=True).data)


class FalseAlarmView(APIView):
    """POST /api/night/false-alarm {"night": <uuid>?} → the last scare was a false alarm."""

    def post(self, request):
        repositories = dependencies.get_repositories()
        night_id = _night_id(request, request.data)
        night = repositories.nights.find(night_id) if night_id else repositories.nights.latest()
        if not night:
            return Response({"detail": "There is no night."}, status=status.HTTP_404_NOT_FOUND)
        try:
            event = MarkFalseAlarmCommand(repositories).execute(MarkFalseAlarmCommandDTO(night_id=night.id))
        except NothingToMark:
            return Response({"detail": "No scares yet tonight."}, status=status.HTTP_409_CONFLICT)
        return Response(ScareEventSerializer(event).data)
