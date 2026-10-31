"""The scares in a folder: any video, gif or image, paired with the sound of the same name."""
import glob
import json
import os
import random
import shutil
import subprocess

from domain.entities.scare import LANG_TAG, Scare
from domain.repositories.scare_catalog_repository import ScareCatalogRepository

VIDEO_EXT = (".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v")
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp", ".bmp")
GIF_EXT = (".gif",)
SOUND_EXT = (".wav", ".ogg", ".mp3")


def extract_audio(video, cache):
    """If your video has sound and there is no .wav next to it, extract it with ffmpeg."""
    if not shutil.which("ffmpeg"):
        return None
    os.makedirs(cache, exist_ok=True)
    out = os.path.join(cache, os.path.splitext(os.path.basename(video))[0] + ".wav")
    if os.path.exists(out):
        return out
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-vn", "-ac", "2", "-ar", "44100", out])
    return out if r.returncode == 0 and os.path.exists(out) and os.path.getsize(out) > 1000 else None


class FileScareCatalogRepository(ScareCatalogRepository):
    def load(self, folder, lang=None):
        folder = str(folder)
        files = sorted(glob.glob(os.path.join(folder, "*")))
        sounds = [f for f in files if f.lower().endswith(SOUND_EXT)
                  and not (lang and LANG_TAG.search(os.path.splitext(os.path.basename(f))[0])
                           and not os.path.splitext(f)[0].endswith("." + lang))]
        by_stem = {os.path.splitext(os.path.basename(s))[0]: s for s in sounds}
        try:
            with open(os.path.join(folder, "_jumps.json")) as fh:
                jumps = json.load(fh)
        except (FileNotFoundError, json.JSONDecodeError):
            jumps = {}
        scares = []
        for f in files:
            base = os.path.basename(f)
            if base.startswith("_") or not f.lower().endswith(VIDEO_EXT + IMAGE_EXT + GIF_EXT):
                continue
            stem = os.path.splitext(base)[0]
            tag = LANG_TAG.search(stem)
            if tag and lang and tag.group(1) != lang:
                continue
            snd = by_stem.get(stem)
            if snd is None and f.lower().endswith(VIDEO_EXT):
                snd = extract_audio(f, os.path.join(folder, ".cache"))
            if snd is None and sounds:
                snd = random.choice(sounds)
            scares.append(Scare(f, snd, float(jumps.get(stem, 0.0))))
        return scares
