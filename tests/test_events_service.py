from datetime import datetime, timedelta, timezone

import pytest
from src.services.errors import ConflictError, NotFoundError
from src.services.events import BlockedUserError, EventsService, utc_now

NOW = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)


class FakeEventsRepository:
    def __init__(self):
        self.events = [
            {
                "id": 1,
                "title": "Upcoming Lab",
                "description": "Lab desc",
                "room_name": "Room 101",
                "status": "published",
                "start_time": NOW + timedelta(days=1),
                "reservation_open": NOW - timedelta(hours=1),
                "reservation_close": NOW + timedelta(hours=23),
                "duration_minutes": 90,
                "seats": 20,
                "free_seats": 19,
            }
        ]
        self.registrations = []
        self.saved_events = []
        self.vanish_on_lock = False

    def get_upcoming_published_events(self):
        return self.events

    def get_event(self, event_id: int):
        return next((e for e in self.events if e["id"] == event_id), None)

    def create_registration_if_seat_free(self, user_id: int, event_id: int):
        event = None if self.vanish_on_lock else self.get_event(event_id)
        if event is None:
            return "missing", None
        for r in self.registrations:
            if r["user_id"] == user_id and r["event_id"] == event_id:
                return "duplicate", r
        if sum(1 for r in self.registrations if r["event_id"] == event_id) >= event["seats"]:
            return "full", None
        record = {"id": len(self.registrations) + 1, "user_id": user_id, "event_id": event_id}
        self.registrations.append(record)
        return "created", record

    def create_saved_event(self, user_id: int, event_id: int):
        for s in self.saved_events:
            if s["user_id"] == user_id and s["event_id"] == event_id:
                return s
        record = {"id": len(self.saved_events) + 1, "user_id": user_id, "event_id": event_id}
        self.saved_events.append(record)
        return record


ACTIVE = {"id": 1, "email": "active@example.com", "role": "user", "is_blocked": False}
BLOCKED = {"id": 2, "email": "blocked@example.com", "role": "user", "is_blocked": True}


def make_service(repo=None):
    return EventsService(repo or FakeEventsRepository(), now=lambda: NOW)


def test_utc_now_is_timezone_aware():
    assert utc_now().tzinfo is not None


def test_events_service_get_upcoming_events():
    service = make_service()

    events = service.get_upcoming_events(ACTIVE)
    assert len(events) == 1
    assert events[0]["title"] == "Upcoming Lab"

    events_blocked = service.get_upcoming_events(BLOCKED)
    assert len(events_blocked) == 1


def test_events_service_sign_up_and_blocked():
    repo = FakeEventsRepository()
    service = make_service(repo)

    reg = service.sign_up(ACTIVE, event_id=1)
    assert reg["user_id"] == 1
    assert reg["event_id"] == 1

    with pytest.raises(BlockedUserError, match="Your account is blocked"):
        service.sign_up(BLOCKED, event_id=1)
    assert len(repo.registrations) == 1


def test_events_service_save_event_and_blocked():
    repo = FakeEventsRepository()
    service = make_service(repo)

    saved = service.save_event(ACTIVE, event_id=1)
    assert saved["user_id"] == 1
    assert saved["event_id"] == 1

    with pytest.raises(BlockedUserError, match="Your account is blocked"):
        service.save_event(BLOCKED, event_id=1)
    assert len(repo.saved_events) == 1


def test_saving_an_event_twice_keeps_one_saved_row():
    repo = FakeEventsRepository()
    service = make_service(repo)

    first = service.save_event(ACTIVE, event_id=1)
    second = service.save_event(ACTIVE, event_id=1)
    assert first == second
    assert len(repo.saved_events) == 1


def test_sign_up_and_save_refuse_unknown_and_unpublished_events():
    repo = FakeEventsRepository()
    repo.events.append({**repo.events[0], "id": 2, "status": "draft"})
    service = make_service(repo)

    for event_id in (99, 2):
        with pytest.raises(NotFoundError, match="Event not found"):
            service.sign_up(ACTIVE, event_id=event_id)
        with pytest.raises(NotFoundError, match="Event not found"):
            service.save_event(ACTIVE, event_id=event_id)
    assert repo.registrations == []
    assert repo.saved_events == []


@pytest.mark.parametrize(
    "change",
    [
        {"start_time": NOW - timedelta(minutes=1)},
        {"reservation_open": NOW + timedelta(minutes=1)},
        {"reservation_close": NOW - timedelta(minutes=1)},
    ],
    ids=["event already started", "reservation not open yet", "reservation already closed"],
)
def test_sign_up_is_refused_outside_the_reservation_window(change):
    repo = FakeEventsRepository()
    repo.events[0].update(change)
    service = make_service(repo)

    with pytest.raises(ConflictError, match="Reservation is not open"):
        service.sign_up(ACTIVE, event_id=1)
    assert repo.registrations == []


def test_sign_up_without_a_reservation_window_is_allowed():
    repo = FakeEventsRepository()
    repo.events[0].update(reservation_open=None, reservation_close=None)

    assert make_service(repo).sign_up(ACTIVE, event_id=1)["event_id"] == 1


def test_signing_up_twice_is_refused():
    repo = FakeEventsRepository()
    service = make_service(repo)
    service.sign_up(ACTIVE, event_id=1)

    with pytest.raises(ConflictError, match="You are already signed up"):
        service.sign_up(ACTIVE, event_id=1)
    assert len(repo.registrations) == 1


def test_sign_up_for_a_full_event_is_refused():
    repo = FakeEventsRepository()
    repo.events[0]["seats"] = 1
    service = make_service(repo)
    service.sign_up(ACTIVE, event_id=1)

    other = {**ACTIVE, "id": 3}
    with pytest.raises(ConflictError, match="This event is full"):
        service.sign_up(other, event_id=1)
    assert len(repo.registrations) == 1


def test_event_deleted_between_check_and_sign_up_is_not_found():
    repo = FakeEventsRepository()
    repo.vanish_on_lock = True

    with pytest.raises(NotFoundError, match="Event not found"):
        make_service(repo).sign_up(ACTIVE, event_id=1)
