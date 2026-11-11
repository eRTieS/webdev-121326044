from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from src.main import app
from src.routes.auth import COOKIE_NAME, get_auth_service
from src.routes.events import get_events_service
from src.services.auth import AuthService
from src.services.events import EventsService
from tests.test_auth_service import FakeUsersRepository


class Slice1EventsRepository:
    def __init__(self):
        now = datetime.now(timezone.utc)
        self.all_events = [
            # 1. Published event starting tomorrow
            {
                "id": 1,
                "title": "Advanced Python Lab",
                "description": "Lab desc",
                "room_name": "Room 101",
                "start_time": (now + timedelta(days=1)).isoformat(),
                "duration_minutes": 90,
                "seats": 20,
                "free_seats": 19,
                "status": "published",
                "is_future": True,
            },
            # 2. Unpublished (draft) event
            {
                "id": 2,
                "title": "Draft Robotics Workshop",
                "description": "Draft desc",
                "room_name": "Lab 202",
                "start_time": (now + timedelta(days=1)).isoformat(),
                "duration_minutes": 120,
                "seats": 15,
                "free_seats": 15,
                "status": "draft",
                "is_future": True,
            },
            # 3. Published event whose start time is an hour ago
            {
                "id": 3,
                "title": "Introductory Linux Lab",
                "description": "Past desc",
                "room_name": "Room 101",
                "start_time": (now - timedelta(hours=1)).isoformat(),
                "duration_minutes": 60,
                "seats": 20,
                "free_seats": 20,
                "status": "published",
                "is_future": False,
            },
        ]
        self.registrations = []
        self.saved_events = []

    def get_upcoming_published_events(self):
        # Emulates: WHERE status = 'published' AND start_time > NOW()
        return [
            e for e in self.all_events
            if e["status"] == "published" and e["is_future"]
        ]

    def create_registration(self, user_id: int, event_id: int):
        rec = {"id": len(self.registrations) + 1, "user_id": user_id, "event_id": event_id}
        self.registrations.append(rec)
        return rec

    def create_saved_event(self, user_id: int, event_id: int):
        rec = {"id": len(self.saved_events) + 1, "user_id": user_id, "event_id": event_id}
        self.saved_events.append(rec)
        return rec


def test_AC_4_upcoming_events_shows_only_future_published_with_room_and_seats():
    """[AC-4] The database holds a published event that starts tomorrow, an unpublished event, and a published event whose start time is an hour ago. A signed-in user sees only the first one in the list, with its room, start time and free seats."""
    users_repo = FakeUsersRepository()
    events_repo = Slice1EventsRepository()

    auth_service = AuthService(users_repo, session_secret="test-secret", default_iterations=1000)
    events_service = EventsService(events_repo)

    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_events_service] = lambda: events_service

    client = TestClient(app)

    # Register and sign in user
    reg = client.post("/api/auth/register", json={"email": "student@tu-sofia.bg", "password": "StudentPass123!"})
    assert reg.status_code == 201
    cookie_val = reg.cookies[COOKIE_NAME]
    client.cookies.set(COOKIE_NAME, cookie_val)

    # Request upcoming events
    resp = client.get("/api/events/upcoming")
    assert resp.status_code == 200
    events = resp.json()

    # Must see ONLY the first one (published, starts tomorrow)
    assert len(events) == 1
    event = events[0]
    assert event["title"] == "Advanced Python Lab"
    assert event["room_name"] == "Room 101"
    assert event["free_seats"] == 19
    assert "start_time" in event


def test_AC_5_blocked_user_login_sees_message_signup_save_refused_403():
    """[AC-5] A blocked user signs in, sees 'Your account is blocked' and can browse the events list. The Sign up and Save buttons are not shown, a direct request to sign up or save is refused with 403, and no row appears in registrations or saved_events."""
    users_repo = FakeUsersRepository()
    events_repo = Slice1EventsRepository()

    auth_service = AuthService(users_repo, session_secret="test-secret", default_iterations=1000)
    events_service = EventsService(events_repo)

    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_events_service] = lambda: events_service

    client = TestClient(app)

    # Register blocked user directly in repository
    from src.services.auth import hash_password
    pwd_hash = hash_password("BlockedPass123!", iterations=1000)
    users_repo.create_user("blocked@tu-sofia.bg", pwd_hash, role="user", is_blocked=True)

    # Sign in
    login_resp = client.post("/api/auth/login", json={"email": "blocked@tu-sofia.bg", "password": "BlockedPass123!"})
    assert login_resp.status_code == 200
    data = login_resp.json()
    assert data["is_blocked"] is True

    cookie_val = login_resp.cookies[COOKIE_NAME]
    client.cookies.set(COOKIE_NAME, cookie_val)

    # Blocked user can browse the events list
    list_resp = client.get("/api/events/upcoming")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    # Direct request to sign up is refused with 403
    signup_resp = client.post("/api/events/1/register")
    assert signup_resp.status_code == 403
    assert signup_resp.json()["detail"] == "Your account is blocked"
    assert len(events_repo.registrations) == 0

    # Direct request to save is refused with 403
    save_resp = client.post("/api/events/1/save")
    assert save_resp.status_code == 403
    assert save_resp.json()["detail"] == "Your account is blocked"
    assert len(events_repo.saved_events) == 0
