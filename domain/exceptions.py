class ScareTVError(Exception):
    """Scare-TV domain error."""


class NightNotFound(ScareTVError):
    pass


class NoScaresAvailable(ScareTVError):
    def __init__(self, folder=""):
        super().__init__(f"No scares in {folder}. Run: make scares (or make realistic for Scare-TV 2)")


class NothingToMark(ScareTVError):
    pass


class InvalidScareKind(ScareTVError):
    pass
