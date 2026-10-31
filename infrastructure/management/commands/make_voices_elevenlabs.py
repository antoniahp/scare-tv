"""python manage.py make_voices_elevenlabs --lang es   (or: make voices-elevenlabs). Optional."""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "OPTIONAL: more realistic voices and screams with ElevenLabs (asks for your key; never stores it)."

    def add_arguments(self, parser):
        parser.add_argument("--lang", choices=["es", "en"], default="es")
        parser.add_argument("--no-sfx", action="store_true")

    def handle(self, *args, **options):
        from infrastructure.services import elevenlabs_voice_generator

        argv = ["--lang", options["lang"]] + (["--no-sfx"] if options["no_sfx"] else [])
        elevenlabs_voice_generator.main(argv)
