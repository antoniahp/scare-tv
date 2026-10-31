"""
OPTIONAL: much more realistic voices and screams with ElevenLabs.

    make voices-elevenlabs

Asks for your ElevenLabs key (it is never stored; ELEVENLABS_API_KEY also works).
Crea:
  media/voices/<language>/*.wav   the live-scare lines, spoken by a real voice and then "possessed"
  media/sfx/*.wav|mp3             screams, growls and laughs from their sound effects model

Scare-TV picks them up automatically if they exist. Otherwise it keeps using the Mac's voice.
It costs a few ElevenLabs credits (8 short lines + 6 three-second effects).
"""
import argparse
import getpass
import json
import os
import sys
import urllib.error
import urllib.request

import numpy as np

from domain.rules.voice_lines import LINES
from infrastructure.services import mac_say_voice_service as voices
from infrastructure.services.synth import horror_audio as ha

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
API = "https://api.elevenlabs.io/v1"
VOICE = os.getenv("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")   # a deep premade voice; change it if you like

SFX = {
    "scream_woman": "a woman screaming in pure terror, horror movie, close and loud, short",
    "scream_man": "a man screaming in terror, horror film jump scare, short and loud",
    "demon_growl": "a deep demonic growl with distorted breathing, horror, close up",
    "child_laugh": "a creepy little girl giggling softly in an empty dark hallway, reverb",
    "violin_stab": "horror movie violin stabs, shrieking dissonant strings jump scare",
    "breath_ear": "slow heavy creepy breathing right next to your ear, horror",
}


def post(path, body, key, fmt):
    req = urllib.request.Request(f"{API}{path}?output_format={fmt}", data=json.dumps(body).encode(),
                                 headers={"xi-api-key": key, "Content-Type": "application/json", "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read(), r.headers.get("Content-Type", "")


def is_mp3(data, ctype):
    return "mpeg" in ctype or data[:3] == b"ID3" or (len(data) > 1 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", choices=["es", "en"], default="es")
    ap.add_argument("--media", default=os.path.join(HERE, "media"))
    ap.add_argument("--no-sfx", action="store_true", help="Voices only, no sound effects")
    a = ap.parse_args(argv)
    key = os.getenv("ELEVENLABS_API_KEY") or getpass.getpass("ElevenLabs key (hidden while typing): ").strip()
    if not key:
        sys.exit("Without a key I cannot use ElevenLabs. Scare-TV will keep using the Mac's voice.")

    vdir = voices.folder(a.media, a.lang)
    os.makedirs(vdir, exist_ok=True)
    for name, (text, style) in LINES[a.lang].items():
        try:
            data, ctype = post(f"/text-to-speech/{VOICE}", {
                "text": text, "model_id": "eleven_multilingual_v2",
                "voice_settings": {"stability": 0.25, "similarity_boost": 0.8, "style": 0.7}}, key, "pcm_24000")
            for old in (".wav", ".mp3"):
                if os.path.exists(os.path.join(vdir, name + old)):
                    os.remove(os.path.join(vdir, name + old))
            if is_mp3(data, ctype):
                open(os.path.join(vdir, name + ".mp3"), "wb").write(data)       # unprocessed, but it works
            else:
                x = np.frombuffer(data[: len(data) // 2 * 2], "<i2").astype(float) / 32768
                ha.write_wav(os.path.join(vdir, name + ".wav"), ha.demon_voice(x, 24000, style))
            print(f"  voice ✓ {name}: {text}")
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors="ignore")[:200]
            sys.exit(f"ElevenLabs answered {e.code}: {msg}\n(is the key right? any credits left?)")
        except urllib.error.URLError as e:
            sys.exit(f"Cannot reach ElevenLabs: {e.reason}")

    if a.no_sfx:
        return
    sdir = os.path.join(a.media, "sfx")
    os.makedirs(sdir, exist_ok=True)
    for name, prompt in SFX.items():
        try:
            data, ctype = post("/sound-generation", {"text": prompt, "duration_seconds": 3.0, "prompt_influence": 0.6},
                               key, "mp3_44100_128")
            open(os.path.join(sdir, name + ".mp3"), "wb").write(data)
            print(f"  efecto ✓ {name}")
        except urllib.error.HTTPError as e:
            print(f"  efecto ✗ {name}: {e.code} {e.read().decode(errors='ignore')[:120]}")
    print("Done. Start Scare-TV as usual: it will use these voices and effects.")
