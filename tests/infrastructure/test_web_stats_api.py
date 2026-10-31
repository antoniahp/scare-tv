"""Anonymous stats from the web mirror: the browser sends numbers only."""
import pytest
from rest_framework.test import APIClient


@pytest.fixture
def client(db):
    return APIClient()


def _visit(client, lang="es"):
    r = client.post("/api/web/visits", {"lang": lang}, format="json")
    assert r.status_code == 201
    return r.json()["visit"]


def test_a_visit_records_scares_and_ranks_each_jump(client):
    visit = _visit(client)
    first = client.post("/api/web/scares", {"visit": visit, "effect": "grin", "flinch": 1.5, "wait_seconds": 1.3}, format="json")
    assert first.status_code == 201 and first.json() == {"rank": None, "scares": 1}
    bigger = client.post("/api/web/scares", {"visit": visit, "effect": "black_eyes", "flinch": 3.0, "fled": True}, format="json")
    assert bigger.json() == {"rank": 100, "scares": 2}
    smaller = client.post("/api/web/scares", {"visit": _visit(client, "en"), "effect": "melt", "flinch": 0.2}, format="json")
    assert smaller.json()["rank"] == 0

    s = client.get("/api/web/summary").json()
    assert s["visits"] == 2 and s["arrivals"] == 2 and s["scares"] == 3          # one person per visit
    assert s["live"]["fled"] == 1 and s["live"]["flinch_mean"] == round((1.5 + 3.0 + 0.2) / 3, 2)
    md = client.get("/api/web/summary?md=1").content.decode()
    assert "Visits: **2**" in md and "| black_eyes | 1 | 3.0 | 1 |" in md


def test_web_visits_do_not_count_as_tv_nights(client):
    client.post("/api/web/scares", {"visit": _visit(client), "effect": "grin", "flinch": 1.0}, format="json")
    assert client.get("/api/night/summary").status_code == 404


def test_only_sane_numbers_are_accepted(client):
    visit = _visit(client)
    bad = client.post("/api/web/scares", {"visit": visit, "effect": "evil", "flinch": 999, "image": "data:..."}, format="json")
    assert bad.status_code == 400 and set(bad.json()) == {"effect", "flinch"}
    unknown = client.post("/api/web/scares", {"visit": "00000000-0000-4000-8000-000000000000", "effect": "grin"}, format="json")
    assert unknown.status_code == 404
    assert client.post("/api/web/visits", {"lang": "fr"}, format="json").status_code == 400
