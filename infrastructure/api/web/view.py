"""Anonymous stats from the web mirror (DRF). The browser only sends numbers: which scare, how far the face
moved and whether it left the frame. No image, video or sound ever reaches the server."""
from django.http import HttpResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from application.commands.record_arrival.command import RecordArrivalCommand
from application.commands.record_arrival.command_dto import RecordArrivalCommandDTO
from application.commands.record_scare.command import RecordScareCommand
from application.commands.record_scare.command_dto import RecordScareCommandDTO
from application.commands.start_night.command import StartNightCommand
from application.commands.start_night.command_dto import StartNightCommandDTO
from application.queries.get_flinch_rank.query import GetFlinchRankQuery
from application.queries.get_flinch_rank.query_dto import GetFlinchRankQueryDTO
from application.queries.get_media_summary.query import GetMediaSummaryQuery
from application.queries.get_media_summary.query_dto import GetMediaSummaryQueryDTO
from domain.entities import ScareEvent
from domain.exceptions import NightNotFound
from domain.rules.night_summary import web_markdown
from infrastructure import dependencies
from infrastructure.api.web.serializer import VisitSerializer, WebScareSerializer

WEB = "web"


class WebThrottle(AnonRateThrottle):
    rate = "60/min"


class VisitView(APIView):
    """POST /api/web/visits {"lang": "es"|"en"} → {"visit": <uuid>}: someone opened the mirror and allowed the camera."""

    throttle_classes = [WebThrottle]

    def post(self, request):
        data = VisitSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        night = StartNightCommand(dependencies.get_repositories()).execute(StartNightCommandDTO(lang=data.validated_data["lang"], media=WEB))
        return Response({"visit": str(night.id)}, status=status.HTTP_201_CREATED)


class WebScareView(APIView):
    """POST /api/web/scares {visit, effect, face_seen, flinch, fled, wait_seconds} → {"rank": 0-100 | null, "scares": n}.

    `rank` is the percentage of earlier scares that jumped less than this one."""

    throttle_classes = [WebThrottle]

    def post(self, request):
        data = WebScareSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        d = data.validated_data
        repositories = dependencies.get_repositories()
        night = repositories.nights.find(d["visit"])
        if not night or night.media != WEB:
            return Response({"detail": "Unknown visit."}, status=status.HTTP_404_NOT_FOUND)
        rank = GetFlinchRankQuery(repositories).execute(GetFlinchRankQueryDTO(flinch=d["flinch"], media=WEB))
        try:
            person = repositories.nights.last_arrival(night) or RecordArrivalCommand(repositories).execute(RecordArrivalCommandDTO(night_id=night.id))
            RecordScareCommand(repositories).execute(RecordScareCommandDTO(arrival_id=person.id,
                night_id=night.id, kind=ScareEvent.LIVE, name=d["effect"], face_seen=d["face_seen"],
                flinch=None if d["flinch"] is None else round(d["flinch"], 2), fled=d["fled"],
                wait_seconds=None if d["wait_seconds"] is None else round(d["wait_seconds"], 1),
                trigger="web_dark" if d["mode"] == "dark" else "web"))
        except NightNotFound:
            return Response({"detail": "Unknown visit."}, status=status.HTTP_404_NOT_FOUND)
        return Response({"rank": rank, "scares": len(repositories.nights.scares(night))}, status=status.HTTP_201_CREATED)


class WebSummaryView(APIView):
    """GET /api/web/summary → stats of every visit together. Add ?md=1 for a markdown table."""

    def get(self, request):
        summary = GetMediaSummaryQuery(dependencies.get_repositories()).execute(GetMediaSummaryQueryDTO(media=WEB))
        if request.query_params.get("md"):
            return HttpResponse(web_markdown(summary) + "\n", content_type="text/plain; charset=utf-8")
        return Response(summary)
