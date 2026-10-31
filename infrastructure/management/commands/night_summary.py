"""python manage.py night_summary   (or: make summary)"""
import time

from django.core.management.base import BaseCommand

from application.queries.get_night_summary.query import GetNightSummaryQuery
from application.queries.get_night_summary.query_dto import GetNightSummaryQueryDTO
from domain.exceptions import NightNotFound
from domain.rules.night_summary import as_markdown
from infrastructure import dependencies


class Command(BaseCommand):
    help = "Prints the summary of the latest night (or the one given with --night)."

    def add_arguments(self, parser):
        parser.add_argument("--night", default=None)

    def handle(self, *args, **options):
        try:
            s = GetNightSummaryQuery(dependencies.get_repositories()).execute(GetNightSummaryQueryDTO(night_id=options["night"]))
        except NightNotFound:
            self.stdout.write("No nights yet. Start the TV with: make run")
            return
        self.stdout.write(as_markdown(s, time.strftime("%Y-%m-%d")))
