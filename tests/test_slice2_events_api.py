import os
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from src.data.db import get_cursor
from src.data.events import EventsRepository
from src.data.users import UsersRepository
from src.main import app
from src.routes.auth import COOKIE_NAME

TEST_DB = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DB, reason="TEST_DATABASE_URL is not set")


def event_id(title: str) -> int:
    with get_cursor(TEST_DB) as cur:
        cur.execute("SELECT id FROM events WHERE title = %s;", (title,))
        return cur.fetchone()["id"]


def user_id(email: str) -> int:
    return UsersRepository(TEST_DB).get_user_by_email(email)["id"]


def login(client: TestClient, email: str, passwords: dict[str, str]) -> None:
    resp = client.post("/api/auth/login", json={"email": email, "password": passwords[email]})
    assert resp.status_code == 200
    cookie_val = resp.cookies.get(COOKIE_NAME)
    if cookie_val:
        client.cookies.set(COOKIE_NAME, cookie_val)


def count_rows(table: str, **kwargs) -> int:
    where = " AND ".join(f"{k} = %s" for k in kwargs)
    sql = f"SELECT COUNT(*) AS c FROM {table}" + (f" WHERE {where}" if where else "") + ";"
    with get_cursor(TEST_DB) as cur:
        cur.execute(sql, tuple(kwargs.values()))
        return cur.fetchone()["c"]


def free_seats(event_id_val: int) -> int:
    repo = EventsRepository(TEST_DB)
    for e in repo.get_upcoming_published_events():
        if e["id"] == event_id_val:
            return e["free_seats"]
    event = repo.get_event(event_id_val)
    taken = count_rows("registrations", event_id=event_id_val)
    return max(0, event["seats"] - taken)


def test_AC_6_user_signs_up_with_free_seats(passwords):
    """[AC-6] A user signs up for an event with free seats and sees "You are signed up".
    One row appears in registrations, and the event's free seats go down by one."""
    lab = event_id("Advanced Python Lab")
    admin = user_id("admin@example.com")
    initial_free = free_seats(lab)
    initial_regs = count_rows("registrations", event_id=lab)

    client = TestClient(app)
    login(client, "admin@example.com", passwords)

    resp = client.post(f"/api/events/{lab}/register")
    assert resp.status_code == 201
    assert resp.json()["message"] == "You are signed up"
    assert count_rows("registrations", event_id=lab, user_id=admin) == 1
    assert count_rows("registrations", event_id=lab) == initial_regs + 1
    assert free_seats(lab) == initial_free - 1


def test_AC_7_user_signs_up_full_event_refused_with_409(passwords):
    """[AC-7] A user who signs up for an event with no free seats sees "This event is full",
    and no new row appears in registrations."""
    lab = event_id("Advanced Python Lab")
    admin = user_id("admin@example.com")

    # Set seats to 1 so student@example.com's existing registration fills the event
    with get_cursor(TEST_DB) as cur:
        cur.execute("UPDATE events SET seats = 1 WHERE id = %s;", (lab,))

    client = TestClient(app)
    login(client, "admin@example.com", passwords)

    initial_regs = count_rows("registrations", event_id=lab)

    resp = client.post(f"/api/events/{lab}/register")
    assert resp.status_code == 409
    assert resp.json()["detail"] == "This event is full"
    assert count_rows("registrations", event_id=lab) == initial_regs
    assert count_rows("registrations", event_id=lab, user_id=admin) == 0


def test_AC_8_user_signs_up_outside_window_refused_with_409(passwords):
    """[AC-8] In events, one event's reservation opens tomorrow and another's closed yesterday.
    A user who tries to sign up for either sees "Reservation is not open", and no new row appears in registrations."""
    now = datetime.now(timezone.utc)
    lab = event_id("Advanced Python Lab")
    admin = user_id("admin@example.com")

    # Event 1: reservation opens tomorrow
    with get_cursor(TEST_DB) as cur:
        cur.execute(
            "UPDATE events SET reservation_open = %s, reservation_close = %s WHERE id = %s;",
            (now + timedelta(days=1), now + timedelta(days=2), lab),
        )

    # Event 2: reservation closed yesterday
    with get_cursor(TEST_DB) as cur:
        cur.execute(
            """
            INSERT INTO events (title, description, room_id, organizer_id, start_time,
                duration_minutes, seats, equipment_count, status, reservation_open, reservation_close)
            SELECT 'Closed Event', 'Desc', room_id, organizer_id, %s,
                60, 10, 5, 'published', %s, %s
            FROM events WHERE id = %s
            RETURNING id;
            """,
            (now + timedelta(days=2), now - timedelta(days=2), now - timedelta(days=1), lab),
        )
        closed_id = cur.fetchone()["id"]

    client = TestClient(app)
    login(client, "admin@example.com", passwords)

    # Try signing up for Event 1 (opens tomorrow)
    resp1 = client.post(f"/api/events/{lab}/register")
    assert resp1.status_code == 409
    assert resp1.json()["detail"] == "Reservation is not open"
    assert count_rows("registrations", event_id=lab, user_id=admin) == 0

    # Try signing up for Event 2 (closed yesterday)
    resp2 = client.post(f"/api/events/{closed_id}/register")
    assert resp2.status_code == 409
    assert resp2.json()["detail"] == "Reservation is not open"
    assert count_rows("registrations", event_id=closed_id, user_id=admin) == 0


def test_AC_9_user_signs_up_with_equipment_or_falls_back(passwords):
    """[AC-9] A user signs up and books a laptop while laptops are left. They see
    "You are signed up with a laptop", and one row appears in equipment_bookings.
    When none are left, the user can still sign up, sees "No equipment left: please bring your own",
    and no row appears in equipment_bookings."""
    lab = event_id("Advanced Python Lab")
    admin = user_id("admin@example.com")
    organizer = user_id("organizer@example.com")

    # Only 1 laptop available for this event
    with get_cursor(TEST_DB) as cur:
        cur.execute("UPDATE events SET equipment_count = 1 WHERE id = %s;", (lab,))

    client1 = TestClient(app)
    login(client1, "admin@example.com", passwords)

    # Admin books the only laptop
    resp1 = client1.post(f"/api/events/{lab}/register?book_equipment=true")
    assert resp1.status_code == 201
    assert resp1.json()["message"] == "You are signed up with a laptop"
    assert count_rows("equipment_bookings", event_id=lab, user_id=admin) == 1

    # Organizer signs up requesting equipment, but none are left
    client2 = TestClient(app)
    login(client2, "organizer@example.com", passwords)

    resp2 = client2.post(f"/api/events/{lab}/register?book_equipment=true")
    assert resp2.status_code == 201
    assert resp2.json()["message"] == "No equipment left: please bring your own"
    assert count_rows("equipment_bookings", event_id=lab, user_id=organizer) == 0
    assert count_rows("registrations", event_id=lab, user_id=organizer) == 1


def test_AC_10_user_cancels_reservation_and_frees_seat_and_equipment(passwords):
    """[AC-10] A user cancels their reservation and sees "Your reservation is cancelled".
    Their rows for that event in registrations and equipment_bookings are gone, and the free seats go up by one."""
    lab = event_id("Advanced Python Lab")
    admin = user_id("admin@example.com")

    client = TestClient(app)
    login(client, "admin@example.com", passwords)

    # Sign up with laptop
    reg_resp = client.post(f"/api/events/{lab}/register?book_equipment=true")
    assert reg_resp.status_code == 201
    assert count_rows("registrations", event_id=lab, user_id=admin) == 1
    assert count_rows("equipment_bookings", event_id=lab, user_id=admin) == 1

    free_before = free_seats(lab)

    # Cancel reservation
    cancel_resp = client.delete(f"/api/events/{lab}/register")
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["message"] == "Your reservation is cancelled"
    assert count_rows("registrations", event_id=lab, user_id=admin) == 0
    assert count_rows("equipment_bookings", event_id=lab, user_id=admin) == 0
    assert free_seats(lab) == free_before + 1


def test_AC_11_cancel_notifies_savers_and_first_to_sign_up_wins(passwords):
    """[AC-11] Two users have saved a full event. A third user cancels their reservation,
    which frees a seat, and both saving users get a notification. The first to sign up
    sees "You are signed up" and has a row in registrations. The second sees "This event is full" and has no row."""
    lab = event_id("Advanced Python Lab")
    student = user_id("student@example.com")
    admin = user_id("admin@example.com")
    organizer = user_id("organizer@example.com")

    # Event has only 1 seat, already taken by student
    with get_cursor(TEST_DB) as cur:
        cur.execute("UPDATE events SET seats = 1 WHERE id = %s;", (lab,))

    client_admin = TestClient(app)
    login(client_admin, "admin@example.com", passwords)

    client_organizer = TestClient(app)
    login(client_organizer, "organizer@example.com", passwords)

    # Both users save the full event
    save1 = client_admin.post(f"/api/events/{lab}/save")
    assert save1.status_code == 200
    save2 = client_organizer.post(f"/api/events/{lab}/save")
    assert save2.status_code == 200
    assert count_rows("saved_events", event_id=lab) == 2
    assert count_rows("notifications", event_id=lab) == 0

    # Student cancels reservation
    client_student = TestClient(app)
    login(client_student, "student@example.com", passwords)
    cancel_resp = client_student.delete(f"/api/events/{lab}/register")
    assert cancel_resp.status_code == 200

    # Both saving users get a notification row
    assert count_rows("notifications", event_id=lab) == 2
    assert count_rows("notifications", event_id=lab, user_id=admin) == 1
    assert count_rows("notifications", event_id=lab, user_id=organizer) == 1

    # First saver signs up and succeeds
    res1 = client_admin.post(f"/api/events/{lab}/register")
    assert res1.status_code == 201
    assert res1.json()["message"] == "You are signed up"
    assert count_rows("registrations", event_id=lab, user_id=admin) == 1

    # Second saver signs up and is refused because event is full again
    res2 = client_organizer.post(f"/api/events/{lab}/register")
    assert res2.status_code == 409
    assert res2.json()["detail"] == "This event is full"
    assert count_rows("registrations", event_id=lab, user_id=organizer) == 0


def test_AC_12_duplicate_signup_refused_with_409(passwords):
    """[AC-12] A user who is already signed up for an event signs up for it again and sees
    "You are already signed up". The request is refused with 409, there is still exactly one
    row for that user and event in registrations, and the event's free seats are unchanged."""
    lab = event_id("Advanced Python Lab")
    student = user_id("student@example.com")
    free_before = free_seats(lab)

    client = TestClient(app)
    login(client, "student@example.com", passwords)

    resp = client.post(f"/api/events/{lab}/register")
    assert resp.status_code == 409
    assert resp.json()["detail"] == "You are already signed up"
    assert count_rows("registrations", event_id=lab, user_id=student) == 1
    assert free_seats(lab) == free_before


def test_AC_13_signup_unknown_or_draft_refused_with_404(passwords):
    """[AC-13] A user tries to sign up for an event id that doesn't exist, and for a draft event.
    Both requests are refused with 404, the user sees "Event not found", and no row appears
    in registrations or equipment_bookings."""
    draft = event_id("Draft Robotics Workshop")
    admin = user_id("admin@example.com")

    client = TestClient(app)
    login(client, "admin@example.com", passwords)

    resp_unknown = client.post("/api/events/999999/register")
    assert resp_unknown.status_code == 404
    assert resp_unknown.json()["detail"] == "Event not found"

    resp_draft = client.post(f"/api/events/{draft}/register")
    assert resp_draft.status_code == 404
    assert resp_draft.json()["detail"] == "Event not found"

    assert count_rows("registrations", user_id=admin, event_id=draft) == 0
    assert count_rows("equipment_bookings", user_id=admin, event_id=draft) == 0


def test_AC_14_signup_past_start_time_refused_with_409(passwords):
    """[AC-14] In events, a published event's start time is set to a minute ago while its
    reservation close is still in the future. A user who tries to sign up for it sees
    "Reservation is not open", the request is refused with 409, and no row appears in registrations."""
    lab = event_id("Advanced Python Lab")
    admin = user_id("admin@example.com")
    now = datetime.now(timezone.utc)

    with get_cursor(TEST_DB) as cur:
        cur.execute(
            "UPDATE events SET start_time = %s, reservation_close = %s WHERE id = %s;",
            (now - timedelta(minutes=1), now + timedelta(days=1), lab),
        )

    client = TestClient(app)
    login(client, "admin@example.com", passwords)

    resp = client.post(f"/api/events/{lab}/register")
    assert resp.status_code == 409
    assert resp.json()["detail"] == "Reservation is not open"
    assert count_rows("registrations", event_id=lab, user_id=admin) == 0


def test_AC_15_cancel_missing_or_unknown_refused_with_404(passwords):
    """[AC-15] A user tries to cancel a reservation they don't have: once for an event they never
    signed up for, and once for an event id that doesn't exist. Both requests are refused with 404,
    the user sees "You have no reservation for this event", and registrations and equipment_bookings are unchanged."""
    lab = event_id("Advanced Python Lab")
    initial_regs = count_rows("registrations")
    initial_equip = count_rows("equipment_bookings")

    client = TestClient(app)
    login(client, "admin@example.com", passwords)

    # Cancel on event they never registered for
    resp1 = client.delete(f"/api/events/{lab}/register")
    assert resp1.status_code == 404
    assert resp1.json()["detail"] == "You have no reservation for this event"

    # Cancel on nonexistent event id
    resp2 = client.delete("/api/events/999999/register")
    assert resp2.status_code == 404
    assert resp2.json()["detail"] == "You have no reservation for this event"

    assert count_rows("registrations") == initial_regs
    assert count_rows("equipment_bookings") == initial_equip


def test_AC_16_save_draft_or_unknown_refused_with_404(passwords):
    """[AC-16] A user tries to save a draft event and an event id that doesn't exist. Both requests
    are refused with 404, the user sees "Event not found", and no row appears in saved_events."""
    draft = event_id("Draft Robotics Workshop")
    student = user_id("student@example.com")

    client = TestClient(app)
    login(client, "student@example.com", passwords)

    resp_unknown = client.post("/api/events/999999/save")
    assert resp_unknown.status_code == 404
    assert resp_unknown.json()["detail"] == "Event not found"

    resp_draft = client.post(f"/api/events/{draft}/save")
    assert resp_draft.status_code == 404
    assert resp_draft.json()["detail"] == "Event not found"

    assert count_rows("saved_events", user_id=student) == 0


def test_AC_17_save_event_twice_is_idempotent(passwords):
    """[AC-17] A user saves the same event twice and sees "Event saved" both times.
    There is exactly one row for that user and event in saved_events."""
    lab = event_id("Advanced Python Lab")
    admin = user_id("admin@example.com")

    client = TestClient(app)
    login(client, "admin@example.com", passwords)

    resp1 = client.post(f"/api/events/{lab}/save")
    assert resp1.status_code == 200
    assert resp1.json()["message"] == "Event saved"

    resp2 = client.post(f"/api/events/{lab}/save")
    assert resp2.status_code == 200
    assert resp2.json()["message"] == "Event saved"

    assert count_rows("saved_events", event_id=lab, user_id=admin) == 1


def test_AC_18_save_event_already_signed_up_refused_with_409(passwords):
    """[AC-18] A user who is signed up for an event tries to save it and sees
    "You are already signed up for this event". The request is refused with 409,
    and no row for that user and event appears in saved_events."""
    lab = event_id("Advanced Python Lab")
    student = user_id("student@example.com")

    client = TestClient(app)
    login(client, "student@example.com", passwords)

    resp = client.post(f"/api/events/{lab}/save")
    assert resp.status_code == 409
    assert resp.json()["detail"] == "You are already signed up for this event"
    assert count_rows("saved_events", event_id=lab, user_id=student) == 0


def test_user_cannot_cancel_another_users_reservation(passwords):
    lab = event_id("Advanced Python Lab")
    admin = user_id("admin@example.com")
    organizer = user_id("organizer@example.com")

    # User A (admin) signs up with a laptop
    client_a = TestClient(app)
    login(client_a, "admin@example.com", passwords)
    reg_resp = client_a.post(f"/api/events/{lab}/register?book_equipment=true")
    assert reg_resp.status_code == 201
    assert count_rows("registrations", event_id=lab, user_id=admin) == 1
    assert count_rows("equipment_bookings", event_id=lab, user_id=admin) == 1

    # User B (organizer) tries to cancel on this event
    client_b = TestClient(app)
    login(client_b, "organizer@example.com", passwords)
    cancel_resp = client_b.delete(f"/api/events/{lab}/register")
    assert cancel_resp.status_code == 404
    assert cancel_resp.json()["detail"] == "You have no reservation for this event"

    # User A's rows in registrations and equipment_bookings are unchanged
    assert count_rows("registrations", event_id=lab, user_id=admin) == 1
    assert count_rows("equipment_bookings", event_id=lab, user_id=admin) == 1


def test_upcoming_events_flags_true_after_signup_and_save_false_for_other(passwords):
    lab = event_id("Advanced Python Lab")
    client_admin = TestClient(app)
    login(client_admin, "admin@example.com", passwords)

    client_organizer = TestClient(app)
    login(client_organizer, "organizer@example.com", passwords)

    # Admin signs up for lab
    reg_resp = client_admin.post(f"/api/events/{lab}/register")
    assert reg_resp.status_code == 201

    # Organizer saves lab
    save_resp = client_organizer.post(f"/api/events/{lab}/save")
    assert save_resp.status_code == 200

    # Admin sees signed_up=True, saved=False
    resp_admin = client_admin.get("/api/events/upcoming")
    assert resp_admin.status_code == 200
    admin_events = [e for e in resp_admin.json() if e["id"] == lab]
    assert len(admin_events) == 1
    assert admin_events[0]["signed_up"] is True
    assert admin_events[0]["saved"] is False

    # Organizer sees signed_up=False, saved=True
    resp_org = client_organizer.get("/api/events/upcoming")
    assert resp_org.status_code == 200
    org_events = [e for e in resp_org.json() if e["id"] == lab]
    assert len(org_events) == 1
    assert org_events[0]["signed_up"] is False
    assert org_events[0]["saved"] is True
