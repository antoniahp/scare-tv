"""python manage.py make_real_scares [--again] [--build-only]   (or: make realistic)"""
from django.conf import settings
from django.core.management.base import BaseCommand

from application.commands.generate_realistic_scares.command import GenerateRealisticScaresCommand
from application.commands.generate_realistic_scares.command_dto import GenerateRealisticScaresCommandDTO
from infrastructure import dependencies


class Command(BaseCommand):
    help = "Scare-TV 2: SD-Turbo imagines realistic horror faces on your Mac and YOLO-pose possesses them."

    def add_arguments(self, parser):
        parser.add_argument("--again", action="store_true", help="Imagine them all again with other seeds")
        parser.add_argument("--build-only", action="store_true", help="Only build the videos from the existing photos")

    def handle(self, *args, **options):
        log = lambda m: self.stdout.write(m)  # noqa: E731
        folder = str(settings.SCARE_TV["REAL_MEDIA_DIR"])
        detector = dependencies.get_person_detector("yolo")
        command = GenerateRealisticScaresCommand(
            dependencies.get_imagination_service(log=log),
            dependencies.get_scare_media_service(detector=detector),
            dependencies.get_possession_service(),
            log=log,
        )
        built = command.execute(GenerateRealisticScaresCommandDTO(folder=folder, again=options["again"], build_only=options["build_only"]))
        self.stdout.write(f"Done: {len(built)} realistic scares in {folder}  (see them in media_real/_catalog_real.jpg)")
