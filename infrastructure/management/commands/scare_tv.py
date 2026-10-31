"""python manage.py scare_tv --display 1   (or simply: make run)"""
import argparse

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Scare-TV: your TV becomes a haunted mirror (webcam + YOLO-pose, 100% local)."

    def add_arguments(self, parser):
        parser.add_argument("--display", type=int, default=0, help="Display to use (the TV is usually 1)")
        parser.add_argument("--list-displays", action="store_true", help="List the connected displays and exit")
        parser.add_argument("--camera", default="0", help="Webcam index (or path to a video, for testing)")
        parser.add_argument("--media", default=str(settings.SCARE_TV["MEDIA_DIR"]), help="Folder with scares (video/gif/image + sound)")
        parser.add_argument("--detector", choices=["auto", "yolo", "motion"], default="auto")
        parser.add_argument("--model", default=str(settings.SCARE_TV["POSE_MODEL"]),
                        help="YOLO weights (open-weight). A -pose model enables live scares with their face")
        parser.add_argument("--live-chance", type=float, default=0.8,
                        help="Probability (0-1) that a scare is LIVE with the person's face (0 = never)")
        parser.add_argument("--no-reaction", dest="reaction", action="store_false",
                        help="Do not show the photo of their scared face at the end")
        parser.add_argument("--no-log", dest="log", action="store_false",
                        help="Do not write the night log (numbers only, never images)")
        parser.add_argument("--no-upload", dest="upload", action="store_false",
                            help="Do not send the night log to the production database (Render)")
        parser.add_argument("--save-reactions", action="store_true",
                        help="Save those photos to reactions/ (ask people for permission first)")
        parser.add_argument("--conf", type=float, default=0.5, help="Minimum confidence to count as a person")
        parser.add_argument("--motion", type=float, default=0.02, help="Motion detector threshold")
        parser.add_argument("--frames", type=int, default=3, help="Consecutive frames seeing someone before the scare")
        parser.add_argument("--cooldown", type=float, default=8.0, help="Minimum seconds between scares")
        parser.add_argument("--rearm", type=float, default=3.0, help="Seconds with nobody there before re-arming")
        parser.add_argument("--repeat", type=float, default=0,
                        help="If the person stays in front, scare again every N seconds (0 = never)")
        parser.add_argument("--order", choices=["random", "sequence"], default="random")
        parser.add_argument("--mirror-chance", type=float, default=0.0, help="Probability (0-1) of using mirror mode")
        parser.add_argument("--idle", default="pumpkin",
                        help="What is shown while waiting: 'pumpkin' (bait), 'black' or the path to an image")
        parser.add_argument("--lang", choices=["es", "en"], default="es",
                        help="Language of the pumpkin, voices and scares with text (es / en)")
        parser.add_argument("--run-seconds", type=float, default=0, help=argparse.SUPPRESS)  # for tests
        parser.add_argument("--volume", type=float, default=1.0)
        parser.add_argument("--max-seconds", type=float, default=8.0, help="Maximum length of each scare")
        parser.add_argument("--windowed", action="store_true", help="Window instead of full screen (for testing)")
        parser.add_argument("--debug", action="store_true", help="Show the camera and the detection")

    def handle(self, *args, **options):
        import pygame

        if options["list_displays"]:
            pygame.display.init()
            for i, s in enumerate(pygame.display.get_desktop_sizes()):
                self.stdout.write(f"  pantalla {i}: {s[0]}x{s[1]}")
            return
        from django.core.management import call_command

        from infrastructure.tv.haunted_tv import ScareTV

        if options["log"]:
            call_command("migrate", verbosity=0)          # the night log is always ready, no extra steps

        ScareTV(argparse.Namespace(**options)).run()
