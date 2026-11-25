import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.routes.events import get_events_service


class SpyEventsService:
    def __init__(self):
        self.calls = []

    def get_upcoming_events(self, user):
        self.calls.append(("get_upcoming_events", user))
        return []

    def sign_up(self, user, event_id, book_equipment=False):
        self.calls.append(("sign_up", user, event_id, book_equipment))
        return {}

    def cancel_reservation(self, user, event_id):
        self.calls.append(("cancel_reservation", user, event_id))
        return {}

    def save_event(self, user, event_id):
        self.calls.append(("save_event", user, event_id))
        return {}


def test_unauthenticated_post_register_refused_with_401():
    spy = SpyEventsService()
    app.dependency_overrides[get_events_service] = lambda: spy
    client = TestClient(app)

    resp = client.post("/api/events/1/register")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Not authenticated"
    assert spy.calls == []


def test_unauthenticated_delete_register_refused_with_401():
    spy = SpyEventsService()
    app.dependency_overrides[get_events_service] = lambda: spy
    client = TestClient(app)

    resp = client.delete("/api/events/1/register")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Not authenticated"
    assert spy.calls == []


def test_unauthenticated_post_save_refused_with_401():
    spy = SpyEventsService()
    app.dependency_overrides[get_events_service] = lambda: spy
    client = TestClient(app)

    resp = client.post("/api/events/1/save")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Not authenticated"
    assert spy.calls == []
