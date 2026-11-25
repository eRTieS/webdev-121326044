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
                "equipment_count": 5,
            }
        ]
        self.registrations = []
        self.saved_events = []
        self.equipment_bookings = []
        self.notifications = []
        self.vanish_on_lock = False

    def get_upcoming_published_events(self, user_id: int | None = None):
        return [
            {
                **e,
                "signed_up": any(r["user_id"] == user_id and r["event_id"] == e["id"] for r in self.registrations),
                "saved": any(s["user_id"] == user_id and s["event_id"] == e["id"] for s in self.saved_events),
            }
            for e in self.events
        ]

    def get_event(self, event_id: int):
        return next((e for e in self.events if e["id"] == event_id), None)

    def get_registration(self, user_id: int, event_id: int):
        return next(
            (r for r in self.registrations if r["user_id"] == user_id and r["event_id"] == event_id),
            None,
        )

    def get_equipment_booking(self, user_id: int, event_id: int):
        return next(
            (b for b in self.equipment_bookings if b["user_id"] == user_id and b["event_id"] == event_id),
            None,
        )

    def create_registration_if_seat_free(self, user_id: int, event_id: int, book_equipment: bool = False):
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

        if not book_equipment:
            return "created", record

        equipment_taken = sum(1 for b in self.equipment_bookings if b["event_id"] == event_id)
        if equipment_taken < event.get("equipment_count", 0):
            booking = {"id": len(self.equipment_bookings) + 1, "user_id": user_id, "event_id": event_id}
            self.equipment_bookings.append(booking)
            return "created_with_equipment", record
        return "created_without_equipment", record

    def cancel_registration(self, user_id: int, event_id: int):
        event = None if self.vanish_on_lock else self.get_event(event_id)
        if event is None:
            return "missing", False
        reg = self.get_registration(user_id, event_id)
        if reg is None:
            return "missing", False
        was_full = sum(1 for r in self.registrations if r["event_id"] == event_id) >= event["seats"]
        self.equipment_bookings = [
            b for b in self.equipment_bookings if not (b["user_id"] == user_id and b["event_id"] == event_id)
        ]
        self.registrations = [
            r for r in self.registrations if not (r["user_id"] == user_id and r["event_id"] == event_id)
        ]
        return "cancelled", was_full

    def create_saved_event(self, user_id: int, event_id: int):
        for s in self.saved_events:
            if s["user_id"] == user_id and s["event_id"] == event_id:
                return s
        record = {"id": len(self.saved_events) + 1, "user_id": user_id, "event_id": event_id}
        self.saved_events.append(record)
        return record

    def delete_saved_event(self, user_id: int, event_id: int):
        prev_len = len(self.saved_events)
        self.saved_events = [
            s for s in self.saved_events if not (s["user_id"] == user_id and s["event_id"] == event_id)
        ]
        return len(self.saved_events) < prev_len

    def get_saver_ids(self, event_id: int):
        return [s["user_id"] for s in self.saved_events if s["event_id"] == event_id]

    def create_notifications(self, user_ids: list[int], event_id: int, message: str):
        created = []
        for uid in user_ids:
            notif = {"id": len(self.notifications) + 1, "user_id": uid, "event_id": event_id, "message": message}
            self.notifications.append(notif)
            created.append(notif)
        return created


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


def test_saving_an_event_you_are_signed_up_for_is_refused():
    repo = FakeEventsRepository()
    service = make_service(repo)
    service.sign_up(ACTIVE, event_id=1)

    with pytest.raises(ConflictError, match="You are already signed up for this event"):
        service.save_event(ACTIVE, event_id=1)
    assert repo.saved_events == []


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


def test_sign_up_returns_message_for_created():
    repo = FakeEventsRepository()
    service = make_service(repo)
    reg = service.sign_up(ACTIVE, event_id=1)
    assert reg["message"] == "You are signed up"


def test_sign_up_with_equipment_allocates_laptop_and_returns_message():
    repo = FakeEventsRepository()
    service = make_service(repo)
    reg = service.sign_up(ACTIVE, event_id=1, book_equipment=True)
    assert reg["message"] == "You are signed up with a laptop"
    assert repo.get_equipment_booking(ACTIVE["id"], 1) is not None


def test_sign_up_with_equipment_when_none_left_returns_fallback_message():
    repo = FakeEventsRepository()
    repo.events[0]["equipment_count"] = 0
    service = make_service(repo)
    reg = service.sign_up(ACTIVE, event_id=1, book_equipment=True)
    assert reg["message"] == "No equipment left: please bring your own"
    assert repo.get_equipment_booking(ACTIVE["id"], 1) is None


def test_sign_up_deletes_saved_event_for_user():
    repo = FakeEventsRepository()
    service = make_service(repo)
    service.save_event(ACTIVE, event_id=1)
    assert len(repo.saved_events) == 1

    service.sign_up(ACTIVE, event_id=1)
    assert len(repo.saved_events) == 0


def test_cancel_reservation_removes_registration_and_equipment():
    repo = FakeEventsRepository()
    service = make_service(repo)
    service.sign_up(ACTIVE, event_id=1, book_equipment=True)
    assert repo.get_registration(ACTIVE["id"], 1) is not None
    assert repo.get_equipment_booking(ACTIVE["id"], 1) is not None

    res = service.cancel_reservation(ACTIVE, event_id=1)
    assert res == {"message": "Your reservation is cancelled"}
    assert repo.get_registration(ACTIVE["id"], 1) is None
    assert repo.get_equipment_booking(ACTIVE["id"], 1) is None


def test_cancel_reservation_missing_raises_not_found():
    repo = FakeEventsRepository()
    service = make_service(repo)
    with pytest.raises(NotFoundError, match="You have no reservation for this event"):
        service.cancel_reservation(ACTIVE, event_id=1)


def test_cancel_reservation_allows_blocked_user_and_unpublished_event():
    repo = FakeEventsRepository()
    repo.events.append({**repo.events[0], "id": 2, "status": "draft"})
    repo.registrations.append({"id": 1, "user_id": BLOCKED["id"], "event_id": 2})
    service = make_service(repo)

    res = service.cancel_reservation(BLOCKED, event_id=2)
    assert res == {"message": "Your reservation is cancelled"}
    assert repo.get_registration(BLOCKED["id"], 2) is None


def test_cancel_reservation_when_full_notifies_savers_in_sofia_time():
    repo = FakeEventsRepository()
    repo.events[0]["seats"] = 1
    user1 = ACTIVE
    user2 = {**ACTIVE, "id": 2, "email": "user2@example.com"}
    user3 = {**ACTIVE, "id": 3, "email": "user3@example.com"}
    service = make_service(repo)

    service.sign_up(user1, event_id=1)
    service.save_event(user2, event_id=1)
    service.save_event(user3, event_id=1)
    assert len(repo.saved_events) == 2

    service.cancel_reservation(user1, event_id=1)
    assert len(repo.notifications) == 2
    # NOW is 2026-11-10 12:00 UTC. Event start_time is NOW + 1 day = 2026-11-11 12:00 UTC.
    # In Europe/Sofia (UTC+2 in November), this is 11 Nov 2026 at 14:00.
    assert (
        repo.notifications[0]["message"]
        == "Upcoming Lab on 11 Nov 2026 at 14:00: a seat has opened up"
    )
    assert repo.notifications[0]["user_id"] == user2["id"]
    assert repo.notifications[1]["user_id"] == user3["id"]


def test_cancel_reservation_when_not_full_does_not_notify_savers():
    repo = FakeEventsRepository()
    repo.events[0]["seats"] = 5
    user1 = ACTIVE
    user2 = {**ACTIVE, "id": 2, "email": "user2@example.com"}
    service = make_service(repo)

    service.sign_up(user1, event_id=1)
    service.save_event(user2, event_id=1)

    service.cancel_reservation(user1, event_id=1)
    assert repo.notifications == []


def test_blocked_user_cannot_sign_up_with_equipment_or_save_event():
    repo = FakeEventsRepository()
    service = make_service(repo)

    with pytest.raises(BlockedUserError, match="Your account is blocked"):
        service.sign_up(BLOCKED, event_id=1, book_equipment=True)
    assert repo.registrations == []
    assert repo.equipment_bookings == []

    with pytest.raises(BlockedUserError, match="Your account is blocked"):
        service.save_event(BLOCKED, event_id=1)
    assert repo.saved_events == []


def test_user_cannot_cancel_another_users_reservation():
    repo = FakeEventsRepository()
    service = make_service(repo)
    user_a = ACTIVE
    user_b = {**ACTIVE, "id": 2, "email": "user_b@example.com"}

    # User A signs up with a laptop
    service.sign_up(user_a, event_id=1, book_equipment=True)
    assert repo.get_registration(user_a["id"], 1) is not None
    assert repo.get_equipment_booking(user_a["id"], 1) is not None

    # User B tries to cancel on this event
    with pytest.raises(NotFoundError, match="You have no reservation for this event"):
        service.cancel_reservation(user_b, event_id=1)

    # User A's registration and laptop booking stay
    assert repo.get_registration(user_a["id"], 1) is not None
    assert repo.get_equipment_booking(user_a["id"], 1) is not None


def test_get_upcoming_events_reports_signed_up_and_saved_flags():
    repo = FakeEventsRepository()
    service = make_service(repo)
    user_a = ACTIVE
    user_b = {**ACTIVE, "id": 2, "email": "user_b@example.com"}

    service.sign_up(user_a, event_id=1)
    service.save_event(user_b, event_id=1)

    events_a = service.get_upcoming_events(user_a)
    assert events_a[0]["signed_up"] is True
    assert events_a[0]["saved"] is False

    events_b = service.get_upcoming_events(user_b)
    assert events_b[0]["signed_up"] is False
    assert events_b[0]["saved"] is True
