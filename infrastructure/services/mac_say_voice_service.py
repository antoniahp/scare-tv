"""
The live-scare voices, offline and free: the system voice (the `say` command on a Mac) turned into a demon,
a whisper in your ear, a broken child, or a high-pitched child speaking very slowly.
They are generated once in <folder>/voices/<language>/ and reused. Your own .wav files (or ElevenLabs ones) win.
"""
import os
import re
import shutil
import subprocess
import tempfile

from domain.rules.voice_lines import LINES
from domain.services.voice_service import VoiceService
from infrastructure.services.synth import horror_audio as ha

PREFERRED = {"es": ["Mónica", "Monica", "Paulina", "Jorge", "Juan", "Marisol"],
             "en": ["Daniel", "Fred", "Ralph", "Alex", "Samantha", "Karen"]}


def pick_say_voice(lang):
    """Finds a voice for the language among the ones installed on the Mac (`say -v ?`)."""
    try:
        out = subprocess.run(["say", "-v", "?"], capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    voices = []
    for line in out.splitlines():
        m = re.match(r"^(.+?)\s{2,}([a-z]{2}[_-][A-Z]{2})", line)
        if m:
            voices.append((m.group(1).strip(), m.group(2)))
    mine = [v for v, loc in voices if loc.lower().startswith(lang)]
    for name in PREFERRED[lang]:
        for v in mine:
            if v.split(" (")[0] == name:
                return v
    return mine[0] if mine else None


def say_to_wav(text, voice, path):
    cmd = ["say", "-o", path, "--file-format=WAVE", "--data-format=LEI16@22050"]
    if voice:
        cmd += ["-v", voice]
    subprocess.run(cmd + [text], check=True, timeout=30, capture_output=True)


def folder(media, lang):
    return os.path.join(media, "voices", lang)


def find(media, lang, key):
    """Path of the prepared voice (wav or mp3), or None."""
    for ext in (".wav", ".mp3"):
        p = os.path.join(folder(media, lang), key + ext)
        if os.path.exists(p):
            return p
    return None


VOICES_VERSION = "2"     # bump it when the voices change: they get rebuilt (ElevenLabs .mp3 files are left alone)


def build(media, lang, log=print, again=False):
    """Builds the missing voices with `say` + effects. Returns how many are ready."""
    out_dir = folder(media, lang)
    os.makedirs(out_dir, exist_ok=True)
    marker = os.path.join(out_dir, "_version.txt")
    stale = again or (open(marker).read().strip() if os.path.exists(marker) else "") != VOICES_VERSION
    todo = [k for k in LINES[lang] if not find(media, lang, k)
            or (stale and find(media, lang, k).endswith(".wav"))]
    if todo and not shutil.which("say"):
        log("[voices] This system has no `say` (Mac only). Live scares will have no voice "
            "unless you put your own .wav files in " + out_dir)
        return len(LINES[lang]) - len(todo)
    voice = pick_say_voice(lang) if todo else None
    if todo:
        log(f"[voices] Preparing {len(todo)} voices ({voice or 'default voice'})… only the first time.")
    for key in todo:
        text, style = LINES[lang][key]
        try:
            with tempfile.TemporaryDirectory() as tmp:
                raw = os.path.join(tmp, "raw.wav")
                say_to_wav(text, voice, raw)
                x, sr = ha.read_wav(raw)
            ha.write_wav(os.path.join(out_dir, key + ".wav"), ha.demon_voice(x, sr, style))
        except Exception as e:  # noqa: BLE001  (a broken voice must not stop the scares)
            log(f"[voices] Could not create '{key}': {e}")
    if shutil.which("say"):
        with open(marker, "w") as f:
            f.write(VOICES_VERSION)
    return sum(1 for k in LINES[lang] if find(media, lang, k))


class MacSayVoiceService(VoiceService):
    def __init__(self, log=print):
        self.log = log

    def build(self, folder, lang, again=False):
        return build(str(folder), lang, log=self.log, again=again)

    def find(self, folder, lang, key):
        return find(str(folder), lang, key)
