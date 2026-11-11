"""Fills a local development database with demo accounts, rooms and events.

Development only: never run it against the deployed database. Run it with
`python -m src.data.seed` after the migrations. Every run gives each demo
account a new random password and prints it once; nothing is stored in the
repository. The events are placed relative to the time of the run, so AC-4
can be checked by hand: one published event tomorrow, one draft, and one
published event that started an hour ago.
"""
import secrets
from datetime import datetime, timedelta, timezone

from src.data.db import get_cursor
from src.services.auth import DEFAULT_ITERATIONS, hash_password

DEMO_ACCOUNTS = [
    ("admin@example.com", "admin", False),
    ("organizer@example.com", "organizer", False),
    ("student@example.com", "user", False),
    ("blocked@example.com", "user", True),
]

DEMO_ROOMS = [("Room 101", 20, 10), ("Lab 202", 15, 15)]


def seed(
    conn_str: str | None = None,
    now: datetime | None = None,
    iterations: int = DEFAULT_ITERATIONS,
) -> dict[str, str]:
    now = now or datetime.now(timezone.utc)
    passwords = {}
    with get_cursor(conn_str) as cur:
        ids = {}
        for email, role, is_blocked in DEMO_ACCOUNTS:
            password = secrets.token_urlsafe(12)
            cur.execute(
                """
                INSERT INTO users (email, password_hash, role, is_blocked)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (email) DO UPDATE
                    SET password_hash = EXCLUDED.password_hash,
                        role = EXCLUDED.role,
                        is_blocked = EXCLUDED.is_blocked
                RETURNING id;
                """,
                (email, hash_password(password, iterations=iterations), role, is_blocked),
            )
            ids[email] = cur.fetchone()["id"]
            passwords[email] = password

        rooms = {}
        for name, seats, equipment in DEMO_ROOMS:
            cur.execute(
                """
                INSERT INTO rooms (name, default_seats, default_equipment)
                VALUES (%s, %s, %s)
                ON CONFLICT (name) DO UPDATE
                    SET default_seats = EXCLUDED.default_seats,
                        default_equipment = EXCLUDED.default_equipment
                RETURNING id;
                """,
                (name, seats, equipment),
            )
            rooms[name] = cur.fetchone()["id"]

        organizer = ids["organizer@example.com"]
        # Re-seeding replaces the demo organizer's events, so their times stay relative to now
        cur.execute("DELETE FROM events WHERE organizer_id = %s;", (organizer,))
        tomorrow = now + timedelta(days=1)
        events = [
            ("Advanced Python Lab", "Lab on FastAPI and async programming", "Room 101",
             tomorrow, 90, 20, 10, "published", now - timedelta(hours=1), tomorrow - timedelta(hours=1)),
            ("Draft Robotics Workshop", "Autonomous rover design", "Lab 202",
             tomorrow, 120, 15, 15, "draft", now + timedelta(hours=12), tomorrow - timedelta(hours=1)),
            ("Introductory Linux Lab", "Introduction to the Linux command line", "Room 101",
             now - timedelta(hours=1), 60, 20, 10, "published", now - timedelta(days=2), now - timedelta(hours=2)),
        ]
        event_ids = []
        for title, description, room, start, minutes, seats, equipment, status, opens, closes in events:
            cur.execute(
                """
                INSERT INTO events (title, description, room_id, organizer_id, start_time,
                    duration_minutes, seats, equipment_count, status, reservation_open, reservation_close)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
                """,
                (title, description, rooms[room], organizer, start, minutes, seats, equipment, status, opens, closes),
            )
            event_ids.append(cur.fetchone()["id"])

        # One registration, so the first event shows 19 of 20 seats free
        cur.execute(
            "INSERT INTO registrations (user_id, event_id) VALUES (%s, %s);",
            (ids["student@example.com"], event_ids[0]),
        )
    return passwords


if __name__ == "__main__":  # pragma: no cover
    from dotenv import load_dotenv

    load_dotenv()
    for email, password in seed().items():
        print(f"{email}  {password}")
