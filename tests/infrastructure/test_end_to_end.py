"""The real TV (pygame with a dummy display and audio), with a video acting as the webcam."""
import importlib.util
import os
import sqlite3
import subprocess
import sys

import cv2
import numpy as np
import pytest
from django.conf import settings

ROOT = str(settings.BASE_DIR)
HAS_YOLO = importlib.util.find_spec("ultralytics") is not None


def run_tv(tmp_path, *args, timeout=120):
    env = {**os.environ, "SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy",
           "SCARE_TV_DB": str(tmp_path / "noches.sqlite3"), "SCARE_TV_LOGS": str(tmp_path / "logs")}
    return subprocess.run([sys.executable, "-u", "manage.py", "scare_tv", "--windowed", *args],
                          cwd=ROOT, capture_output=True, text=True, timeout=timeout, env=env)


def scares_in_db(tmp_path):
    with sqlite3.connect(tmp_path / "noches.sqlite3") as db:
        return db.execute("SELECT kind, name, face_seen, flinch FROM domain_scareevent").fetchall()


def test_runs_end_to_end_with_a_video_as_camera(tmp_path):
    """A 'hallway' where something walks in: at least one scare, written to the log, and a clean exit."""
    path = str(tmp_path / "pasillo.mp4")
    w = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), 15, (320, 180))
    for i in range(90):
        f = np.full((180, 320, 3), 40, np.uint8)
        if 40 <= i < 70:
            cv2.rectangle(f, (100, 20), (220, 170), (220, 220, 220), -1)
        w.write(f)
    w.release()
    r = run_tv(tmp_path, "--detector", "motion", "--camera", path, "--run-seconds", "9",
               "--cooldown", "1", "--rearm", "0.5", "--lang", "en")
    assert r.returncode == 0, r.stderr[-1500:]
    assert "scare:" in r.stdout and "Done. Scares:" in r.stdout
    assert scares_in_db(tmp_path) and list((tmp_path / "logs").glob("summary_*.md"))


@pytest.mark.skipif(not HAS_YOLO, reason="ultralytics no instalado")
def test_live_scare_runs_end_to_end_and_shows_the_reaction(tmp_path):
    import ultralytics

    src = cv2.imread(os.path.join(os.path.dirname(ultralytics.__file__), "assets", "zidane.jpg"))
    path = str(tmp_path / "persona.mp4")
    w = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), 15, (640, 360))
    for i in range(60):
        w.write(cv2.resize(np.roll(src, i * 2, axis=1), (640, 360)))
    w.release()
    r = run_tv(tmp_path, "--camera", path, "--live-chance", "1", "--run-seconds", "16", "--frames", "2", "--idle", "black")
    assert r.returncode == 0, r.stderr[-1500:]
    assert "LIVE scare" in r.stdout, r.stdout[-1500:]
    assert "jump-o-meter" in r.stdout and "Live (their face)" in r.stdout
    live = [row for row in scares_in_db(tmp_path) if row[0] == "live"]
    assert live and live[0][2] == 1 and live[0][3] is not None


def test_list_displays_and_night_summary_commands(tmp_path):
    env = {**os.environ, "SDL_VIDEODRIVER": "dummy", "SCARE_TV_DB": str(tmp_path / "x.sqlite3")}
    r = subprocess.run([sys.executable, "manage.py", "scare_tv", "--list-displays"], cwd=ROOT, capture_output=True, text=True, env=env, timeout=60)
    assert r.returncode == 0 and "pantalla 0" in r.stdout
    subprocess.run([sys.executable, "manage.py", "migrate", "-v0"], cwd=ROOT, env=env, check=True, timeout=60)
    r = subprocess.run([sys.executable, "manage.py", "night_summary"], cwd=ROOT, capture_output=True, text=True, env=env, timeout=60)
    assert r.returncode != 0 or "night" in (r.stdout + r.stderr).lower()
