"""Jump-o-meter scores. Pure Python on purpose: the web service on Render has no numpy."""


def score10(flinch):
    """Eye-distances → a 0 to 10 score for the polaroid."""
    if flinch is None:
        return None
    return int(max(0, min(10, round(flinch * 2.5))))


def jump_level(flinch, fled=False):
    """The jump level stored for each scare and person: the polaroid's 0-10, and 10 for running out of frame."""
    if fled:
        return 10
    return score10(flinch)
