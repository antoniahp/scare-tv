"""python manage.py prepare_voices --lang es   (or: make voices)"""
from django.conf import settings
from django.core.management.base import BaseCommand

from application.commands.prepare_voices.command import PrepareVoicesCommand
from application.commands.prepare_voices.command_dto import PrepareVoicesCommandDTO
from infrastructure import dependencies


class Command(BaseCommand):
    help = "Prepares the live-scare voices from the Mac's own voice (demon, whisper, child…)."

    def add_arguments(self, parser):
        parser.add_argument("--lang", choices=["es", "en"], default="es")
        parser.add_argument("--media", default=str(settings.SCARE_TV["MEDIA_DIR"]))
        parser.add_argument("--again", action="store_true", help="Rebuild the voices even if they already exist")

    def handle(self, *args, **options):
        n = PrepareVoicesCommand(dependencies.get_voice_service(log=self.stdout.write)).execute(
            PrepareVoicesCommandDTO(folder=options["media"], lang=options["lang"], again=options["again"]))
        self.stdout.write(f"{n} voices ready.")
