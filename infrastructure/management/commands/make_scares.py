"""python manage.py make_scares [03 07] [--sounds]   (or: make scares)"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Builds the 20 classic scares (video + sound) and the live-scare sound tracks."

    def add_arguments(self, parser):
        parser.add_argument("numbers", nargs="*", help="Only these scares (e.g. 03 07)")
        parser.add_argument("--sounds", action="store_true", help="Only the sounds (fast)")

    def handle(self, *args, **options):
        from infrastructure.services import procedural_scares

        procedural_scares.main(["--sounds"] if options["sounds"] else options["numbers"])
