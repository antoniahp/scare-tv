import os
import re
from dataclasses import dataclass

LANG_TAG = re.compile(r"\.(es|en)$")


@dataclass(frozen=True)
class Scare:
    """A scare from the folder: the video (or gif or image), its sound and the second it jumps."""

    visual: str
    sound_path: str | None
    jump_at: float = 0.0

    @property
    def name(self):
        return LANG_TAG.sub("", os.path.splitext(os.path.basename(self.visual))[0])

    @property
    def stem(self):
        return os.path.splitext(os.path.basename(self.visual))[0]
