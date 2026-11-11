"""Data-layer tests against a real PostgreSQL database.

They run only when TEST_DATABASE_URL is set, and they wipe that database before
every test, so it must never point at the development or the deployed database.
"""
import os
from datetime import datetime, timezone

import psycopg
import pytest
from src.data.db import get_cursor
from src.data.events import EventsRepository
from src.data.migrate import migrate
from src.data.seed import seed
from src.data.users import UsersRepository
from src.services.auth import verify_password

TEST_DB = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(not TEST_DB, reason="TEST_DATABASE_URL is not set")


@pytest.fixture
def passwords():
    if TEST_DB == os.environ.get("DATABASE_URL"):
        pytest.fail("TEST_DATABASE_URL is the development database; these tests would wipe it")
    with get_cursor(TEST_DB) as cur:
        cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    migrate(TEST_DB)
    return seed(TEST_DB, iterations=1000)


def event_id(title):
    with get_cursor(TEST_DB) as cur:
        cur.execute("SELECT id FROM events WHERE title = %s;", (title,))
        return cur.fetchone()["id"]


def test_migrations_run_once(passwords):
    assert migrate(TEST_DB) == []


def test_seed_gives_each_demo_account_a_working_random_password(passwords):
    repo = UsersRepository(TEST_DB)
    assert set(passwords) == {"admin@example.com", "organizer@example.com", "student@example.com", "blocked@example.com"}
    for email, password in passwords.items():
        assert verify_password(password, repo.get_user_by_email(email)["password_hash"])
    assert repo.get_user_by_email("blocked@example.com")["is_blocked"] is True


def test_seed_can_run_again(passwords):
    seed(TEST_DB, iterations=1000)
    assert len(EventsRepository(TEST_DB).get_upcoming_published_events()) == 1


def test_data_layer_users_repository(passwords):
    repo = UsersRepository(TEST_DB)

    organizer = repo.get_user_by_email("organizer@example.com")
    assert organizer["role"] == "organizer"
    assert repo.get_user_by_id(organizer["id"])["email"] == "organizer@example.com"
    assert repo.get_user_by_email("nonexistent@example.com") is None
    assert repo.get_user_by_id(999999) is None

    created = repo.create_user("New@Example.com", "hash_dummy")
    assert created["email"] == "new@example.com"


def test_unknown_role_is_refused_by_the_database(passwords):
    with pytest.raises(psycopg.errors.CheckViolation):
        UsersRepository(TEST_DB).create_user("x@example.com", "hash_dummy", role="superuser")


def test_upcoming_events_are_published_and_not_started(passwords):
    upcoming = EventsRepository(TEST_DB).get_upcoming_published_events()
    assert len(upcoming) == 1
    assert upcoming[0]["title"] == "Advanced Python Lab"
    assert upcoming[0]["room_name"] == "Room 101"
    assert upcoming[0]["free_seats"] == 19


def test_get_event(passwords):
    repo = EventsRepository(TEST_DB)
    event = repo.get_event(event_id("Draft Robotics Workshop"))
    assert event["status"] == "draft"
    assert event["start_time"] > datetime.now(timezone.utc)
    assert repo.get_event(999999) is None


def test_registration_is_created_once_and_only_while_seats_are_free(passwords):
    repo = EventsRepository(TEST_DB)
    users = UsersRepository(TEST_DB)
    lab = event_id("Advanced Python Lab")
    admin = users.get_user_by_email("admin@example.com")["id"]
    student = users.get_user_by_email("student@example.com")["id"]

    result, row = repo.create_registration_if_seat_free(admin, lab)
    assert result == "created"
    assert repo.get_registration(admin, lab)["id"] == row["id"]

    assert repo.create_registration_if_seat_free(admin, lab)[0] == "duplicate"

    with get_cursor(TEST_DB) as cur:
        cur.execute("UPDATE events SET seats = 2 WHERE id = %s;", (lab,))
    organizer = users.get_user_by_email("organizer@example.com")["id"]
    assert repo.create_registration_if_seat_free(organizer, lab) == ("full", None)
    assert repo.get_registration(student, lab) is not None
    assert repo.get_registration(organizer, lab) is None

    assert repo.create_registration_if_seat_free(admin, 999999) == ("missing", None)


def test_saving_an_event_twice_keeps_one_row(passwords):
    repo = EventsRepository(TEST_DB)
    student = UsersRepository(TEST_DB).get_user_by_email("student@example.com")["id"]
    lab = event_id("Advanced Python Lab")

    assert repo.get_saved_event(student, lab) is None
    first = repo.create_saved_event(student, lab)
    second = repo.create_saved_event(student, lab)
    assert first["id"] == second["id"]


def test_deleting_an_organizer_keeps_their_events(passwords):
    lab = event_id("Advanced Python Lab")
    with get_cursor(TEST_DB) as cur:
        cur.execute("DELETE FROM users WHERE email = 'organizer@example.com';")
        cur.execute("SELECT organizer_id FROM events WHERE id = %s;", (lab,))
        assert cur.fetchone()["organizer_id"] is None
