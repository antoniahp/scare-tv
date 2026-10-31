"""Sends the TV's night log to the production database (the Render web service), numbers only.

The TV keeps writing to its own local database first; this only mirrors each record to
https://scare-tv.onrender.com in a background thread, so a slow or missing connection never delays a scare.
Every record goes with its local id, so retries and `make upload` never duplicate anything.

SCARE_TV_UPLOAD_URL changes the address; SCARE_TV_UPLOAD_URL=off (or --no-upload) switches it off."""
import json
import os
import queue
import threading
import time
import urllib.error
import urllib.request

DEFAULT_URL = "https://scare-tv.onrender.com"


def upload_url():
    url = os.getenv("SCARE_TV_UPLOAD_URL", "").strip()
    if url.lower() in ("off", "no", "0", "false"):
        return None
    if not url and "PYTEST_CURRENT_TEST" in os.environ:      # tests never talk to production
        return None
    return (url or DEFAULT_URL).rstrip("/")


def night_payload(night):
    return {"id": str(night.id), "lang": night.lang, "media": night.media if night.media in ("media", "media_real") else "media",
            "started_at": night.started_at.isoformat(), "ended_at": night.ended_at.isoformat() if night.ended_at else None}


def arrival_payload(arrival):
    return {"id": str(arrival.id), "night": str(arrival.night_id), "created_at": arrival.created_at.isoformat()}


def scare_payload(event):
    return {"id": str(event.id), "night": str(event.night_id), "kind": event.kind, "name": event.name, "face_seen": event.face_seen,
            "flinch": event.flinch, "fled": event.fled, "wait_seconds": event.wait_seconds, "trigger": event.trigger,
            "false_alarm": event.false_alarm, "created_at": event.created_at.isoformat()}


def post(base, path, payload, timeout=20):
    """One POST. Returns the HTTP status, or None if production could not be reached."""
    req = urllib.request.Request(f"{base}/api/tv/{path}", data=json.dumps(payload).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "User-Agent": "scare-tv"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except (urllib.error.URLError, OSError, TimeoutError):
        return None


class ProductionUploader:
    """Queue + one background thread. The first request may wait ~1 min while Render's free plan wakes up."""

    def __init__(self, base=None, log=print):
        self.base, self.log = base, log
        self.q = queue.Queue()
        self.night_ok = False
        self.thread = None
        if self.base:
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()

    @property
    def enabled(self):
        return self.base is not None

    def night(self, night):
        if self.base and night is not None:
            self.q.put(("nights", night_payload(night)))

    def arrival(self, arrival):
        if self.base and arrival is not None:
            self.q.put(("arrivals", arrival_payload(arrival)))

    def scare(self, event):
        if self.base and event is not None:
            self.q.put(("scares", scare_payload(event)))

    def _run(self):
        warned = False
        while True:
            path, payload = self.q.get()
            for attempt in range(6):                # ~2 min in total: enough for Render to wake up
                code = post(self.base, path, payload, timeout=30)
                if code is not None and code < 500 and code != 429:
                    break
                time.sleep(min(30, 2 ** attempt * 2))
            if (code is None or code >= 400) and not warned:
                warned = True
                self.log(f"   (production database not reachable right now: {code}. Scares are still saved locally; `make upload` sends them later)")
            self.q.task_done()

    def flush(self, timeout=20):
        """Give pending uploads a few seconds when the TV is switched off."""
        if not self.thread:
            return
        end = time.time() + timeout
        while self.q.unfinished_tasks and time.time() < end:
            time.sleep(0.2)
