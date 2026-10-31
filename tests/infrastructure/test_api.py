import pytest
from rest_framework.test import APIClient

from application.commands.record_scare.command import RecordScareCommand
from application.commands.record_scare.command_dto import RecordScareCommandDTO
from application.commands.start_night.command import StartNightCommand
from application.commands.start_night.command_dto import StartNightCommandDTO


@pytest.fixture
def client():
    return APIClient()


def test_health(client, db):
    assert client.get("/api/health").json() == {"ok": True}


def test_without_nights_the_api_explains_how_to_start(client, db):
    r = client.get("/api/night/summary")
    assert r.status_code == 404 and "make run" in r.json()["detail"]
    assert client.get("/api/night/scares").json() == []
    assert client.post("/api/night/false-alarm", {}, format="json").status_code == 404


def test_summary_scares_and_false_alarm(client, repositories):
    night = StartNightCommand(repositories).execute(StartNightCommandDTO())
    assert client.post("/api/night/false-alarm", {}, format="json").status_code == 409
    rec = RecordScareCommand(repositories)
    rec.execute(RecordScareCommandDTO(night.id, "live", "melt", face_seen=True, flinch=2.5))
    rec.execute(RecordScareCommandDTO(night.id, "file", "02_the_scream", flinch=0.4))

    s = client.get("/api/night/summary").json()
    assert s["scares"] == 2 and s["live"]["flinch_mean"] == 2.5
    rows = client.get(f"/api/night/scares?night={night.id}").json()
    assert [r["name"] for r in rows] == ["melt", "02_the_scream"]
    assert all("image" not in r and "frame" not in r for r in rows)            # numbers only

    r = client.post("/api/night/false-alarm", {"night": str(night.id)}, format="json")
    assert r.status_code == 200 and r.json()["false_alarm"] is True
    assert client.get("/api/night/summary").json()["scares"] == 1
    assert client.get("/api/night/scares?night=not-a-uuid").status_code == 400


def test_the_web_mirror_is_served_by_django(client, db):
    r = client.get("/")
    assert r.status_code == 200 and b"Scare-TV" in b"".join(r.streaming_content if r.streaming else [r.content])
