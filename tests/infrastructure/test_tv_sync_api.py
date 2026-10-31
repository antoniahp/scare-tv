"""The TVs mirror their night log to production: idempotent, numbers only, and kept apart from web visits."""
import uuid

import pytest
from rest_framework.test import APIClient

from domain.entities import Arrival, Night, ScareEvent
from infrastructure.services import production_uploader as up


@pytest.fixture
def client(db):
    return APIClient()


def _night(client, **kw):
    body = {"id": str(uuid.uuid4()), "lang": "es", "media": "media_real", "started_at": "2026-10-30T19:00:00Z", **kw}
    return body, client.post("/api/tv/nights", body, format="json")


def _scare(night_id, **kw):
    return {"id": str(uuid.uuid4()), "night": night_id, "kind": "live", "name": "black_eyes", "face_seen": True,
            "flinch": 1.2, "fled": False, "wait_seconds": 4.0, "trigger": "auto", "created_at": "2026-10-30T19:05:00Z", **kw}


def test_a_tv_night_its_arrivals_and_scares_reach_production_once(client):
    night, r = _night(client)
    assert r.status_code == 201 and r.json()["created"] is True
    assert client.post("/api/tv/nights", {**night, "ended_at": "2026-10-30T20:00:00Z"}, format="json").status_code == 200
    arrival = {"id": str(uuid.uuid4()), "night": night["id"], "created_at": "2026-10-30T19:04:00Z"}
    assert client.post("/api/tv/arrivals", arrival, format="json").status_code == 201
    assert client.post("/api/tv/arrivals", arrival, format="json").status_code == 200        # a retry: no duplicate
    scare = _scare(night["id"])
    assert client.post("/api/tv/scares", scare, format="json").status_code == 201
    assert client.post("/api/tv/scares", scare, format="json").status_code == 200
    assert client.post("/api/tv/scares", {**scare, "false_alarm": True}, format="json").status_code == 200   # F key, later

    n = Night.objects.get(id=night["id"])
    assert n.ended_at is not None and Arrival.objects.filter(night=n).count() == 1
    e = ScareEvent.objects.get(id=scare["id"])
    assert e.false_alarm and e.flinch == 1.2 and e.created_at.hour == 19
    assert client.get("/api/night/scares").json()[0]["name"] == "black_eyes"


def test_tv_records_cannot_touch_web_visits_or_carry_free_text(client):
    visit = client.post("/api/web/visits", {"lang": "es"}, format="json").json()["visit"]
    assert client.post("/api/tv/nights", {"id": visit, "media": "media"}, format="json").status_code == 409
    assert client.post("/api/tv/scares", _scare(visit), format="json").status_code == 404
    night, _ = _night(client)
    assert client.post("/api/tv/scares", _scare(night["id"], name="<script>alert(1)</script>"), format="json").status_code == 400
    assert client.post("/api/tv/scares", _scare(night["id"], flinch=999), format="json").status_code == 400
    assert client.post("/api/tv/scares", _scare(str(uuid.uuid4())), format="json").status_code == 404
    assert client.post("/api/tv/nights", {"id": str(uuid.uuid4()), "media": "web"}, format="json").status_code == 400


def test_the_uploader_stays_off_in_tests_and_builds_the_same_payloads(repositories, monkeypatch):
    monkeypatch.delenv("SCARE_TV_UPLOAD_URL", raising=False)
    assert up.upload_url() is None                                     # pytest never talks to production
    monkeypatch.setenv("SCARE_TV_UPLOAD_URL", "off")
    assert up.upload_url() is None
    monkeypatch.setenv("SCARE_TV_UPLOAD_URL", "https://example.test/")
    assert up.upload_url() == "https://example.test"
    off = up.ProductionUploader(None)
    off.scare(None)
    assert not off.enabled and off.q.empty()

    night = Night.objects.create(media="media_real")
    event = ScareEvent.prepare(night, "file", "real_01_pale_woman", face_seen=True, flinch=0.58)
    event.save()
    p = up.scare_payload(event)
    assert p["night"] == str(night.id) and p["name"] == "real_01_pale_woman" and set(p) >= {"id", "created_at", "false_alarm"}
    assert up.night_payload(night)["media"] == "media_real"


def test_the_admin_is_there_behind_a_login(client):
    r = client.get("/admin/")
    assert r.status_code == 302 and "/admin/login/" in r["Location"]
    assert client.get("/admin/login/").status_code == 200
