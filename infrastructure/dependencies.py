"""This is where each repository and service gets its real implementation. Tests use fakes."""

from django.conf import settings

from infrastructure.repositories.django_repositories import build_django_repositories


def get_repositories():
    return build_django_repositories()


def get_person_detector(mode="auto", model=None, conf=0.5, motion=0.02):
    from infrastructure.services.yolo_person_detector import YoloPersonDetector

    return YoloPersonDetector(mode, model or str(settings.SCARE_TV["POSE_MODEL"]), conf, motion, base_dir=str(settings.BASE_DIR))


def get_possession_service():
    from infrastructure.services.opencv_possession_service import OpenCvPossessionService

    return OpenCvPossessionService()


def get_voice_service(log=print):
    from infrastructure.services.mac_say_voice_service import MacSayVoiceService

    return MacSayVoiceService(log=log)


def get_imagination_service(log=print):
    from infrastructure.services.sd_turbo_imagination_service import SdTurboImaginationService

    return SdTurboImaginationService(log=log)


def get_scare_media_service(detector=None):
    from infrastructure.services.scare_media_service import FileScareMediaService

    media = settings.SCARE_TV["MEDIA_DIR"]
    return FileScareMediaService(detector=detector, live_tracks_dir=str(media / "live"), ghost_png=str(media / "_mirror_ghost.png"))
