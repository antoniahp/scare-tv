"""`make upload`: sends every TV night in the local database (nights, arrivals, scares) to production.

Safe to run again and again: each record keeps its local id, so production never stores it twice."""
from django.core.management.base import BaseCommand

from domain.entities import Arrival, Night, ScareEvent
from infrastructure.services.production_uploader import (DEFAULT_URL, arrival_payload, night_payload, post, scare_payload,
                                                         upload_url)


class Command(BaseCommand):
    help = "Send the local night log (TV) to the production database on Render"

    def add_arguments(self, parser):
        parser.add_argument("--url", default=None, help=f"Production address (default: SCARE_TV_UPLOAD_URL or {DEFAULT_URL})")

    def handle(self, *args, **opts):
        base = (opts["url"] or upload_url() or DEFAULT_URL).rstrip("/")
        nights = list(Night.objects.exclude(media="web").order_by("started_at"))
        self.stdout.write(f"Sending {len(nights)} nights to {base} (the first request can take ~1 min while Render wakes up)…")
        counts = {"nights": 0, "arrivals": 0, "scares": 0, "failed": 0}

        def send(path, payload, key):
            code = None
            for _ in range(4):
                code = post(base, path, payload, timeout=90)
                if code is not None and code < 500 and code != 429:
                    break
            if code in (200, 201):
                counts[key] += 1
            else:
                counts["failed"] += 1
                self.stderr.write(f"  {path} {payload['id']}: {code}")

        for night in nights:
            send("nights", night_payload(night), "nights")
            for a in Arrival.objects.filter(night=night).order_by("created_at"):
                send("arrivals", arrival_payload(a), "arrivals")
            for e in ScareEvent.objects.filter(night=night).order_by("created_at"):
                send("scares", scare_payload(e), "scares")
        self.stdout.write(self.style.SUCCESS(
            f"Done: {counts['nights']} nights, {counts['arrivals']} arrivals, {counts['scares']} scares in production"
            + (f" · {counts['failed']} failed" if counts["failed"] else "")))
        self.stdout.write(f"See them at {base}/admin/  or  {base}/api/night/scares")
