from typing import Any
from src.data.db import get_cursor


class EventsRepository:
    def __init__(self, conn_str: str | None = None):
        self.conn_str = conn_str

    def get_upcoming_published_events(self) -> list[dict[str, Any]]:
        sql = """
            SELECT 
                e.id,
                e.title,
                e.description,
                e.start_time,
                e.duration_minutes,
                e.seats,
                e.equipment_count,
                e.status,
                r.name AS room_name,
                GREATEST(e.seats - COUNT(reg.id), 0) AS free_seats
            FROM events e
            JOIN rooms r ON e.room_id = r.id
            LEFT JOIN registrations reg ON reg.event_id = e.id
            WHERE e.status = 'published' AND e.start_time > NOW()
            GROUP BY e.id, r.name
            ORDER BY e.start_time ASC;
        """
        with get_cursor(self.conn_str) as cur:
            cur.execute(sql)
            return cur.fetchall()

    def get_event(self, event_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT id, title, status, seats, start_time, reservation_open, reservation_close
            FROM events
            WHERE id = %s;
        """
        with get_cursor(self.conn_str) as cur:
            cur.execute(sql, (event_id,))
            return cur.fetchone()

    def get_registration(self, user_id: int, event_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT id, user_id, event_id, created_at
            FROM registrations
            WHERE user_id = %s AND event_id = %s;
        """
        with get_cursor(self.conn_str) as cur:
            cur.execute(sql, (user_id, event_id))
            return cur.fetchone()

    def get_saved_event(self, user_id: int, event_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT id, user_id, event_id, created_at
            FROM saved_events
            WHERE user_id = %s AND event_id = %s;
        """
        with get_cursor(self.conn_str) as cur:
            cur.execute(sql, (user_id, event_id))
            return cur.fetchone()

    def get_equipment_booking(self, user_id: int, event_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT id, user_id, event_id, created_at
            FROM equipment_bookings
            WHERE user_id = %s AND event_id = %s;
        """
        with get_cursor(self.conn_str) as cur:
            cur.execute(sql, (user_id, event_id))
            return cur.fetchone()

    def create_registration_if_seat_free(
        self, user_id: int, event_id: int, book_equipment: bool = False
    ) -> tuple[str, dict[str, Any] | None]:
        """Returns ("created", row), ("created_with_equipment", row),
        ("created_without_equipment", row), ("duplicate", row),
        ("full", None) or ("missing", None).

        The seat and equipment counts are checked here under the same lock,
        because only a locked event row stops two people taking the last seat or laptop.
        """
        with get_cursor(self.conn_str) as cur:
            cur.execute(
                "SELECT seats, equipment_count FROM events WHERE id = %s FOR UPDATE;",
                (event_id,),
            )
            event = cur.fetchone()
            if event is None:
                return "missing", None
            cur.execute(
                "SELECT id, user_id, event_id, created_at FROM registrations WHERE user_id = %s AND event_id = %s;",
                (user_id, event_id),
            )
            existing = cur.fetchone()
            if existing:
                return "duplicate", existing
            cur.execute("SELECT COUNT(*) AS taken FROM registrations WHERE event_id = %s;", (event_id,))
            if cur.fetchone()["taken"] >= event["seats"]:
                return "full", None
            cur.execute(
                """
                INSERT INTO registrations (user_id, event_id)
                VALUES (%s, %s)
                RETURNING id, user_id, event_id, created_at;
                """,
                (user_id, event_id),
            )
            registration = cur.fetchone()

            if not book_equipment:
                return "created", registration

            cur.execute(
                "SELECT COUNT(*) AS taken FROM equipment_bookings WHERE event_id = %s;",
                (event_id,),
            )
            if cur.fetchone()["taken"] < event["equipment_count"]:
                cur.execute(
                    "INSERT INTO equipment_bookings (user_id, event_id) VALUES (%s, %s);",
                    (user_id, event_id),
                )
                return "created_with_equipment", registration
            else:
                return "created_without_equipment", registration

    def cancel_registration(self, user_id: int, event_id: int) -> tuple[str, bool]:
        """In one transaction, deletes the registration and its equipment booking.

        Returns ("missing", False) if no registration exists, or
        ("cancelled", was_full) reporting whether the event was full before the cancel.
        """
        with get_cursor(self.conn_str) as cur:
            cur.execute("SELECT seats FROM events WHERE id = %s FOR UPDATE;", (event_id,))
            event = cur.fetchone()
            if event is None:
                return "missing", False
            cur.execute(
                "SELECT id FROM registrations WHERE user_id = %s AND event_id = %s;",
                (user_id, event_id),
            )
            if cur.fetchone() is None:
                return "missing", False
            cur.execute(
                "SELECT COUNT(*) AS taken FROM registrations WHERE event_id = %s;",
                (event_id,),
            )
            was_full = cur.fetchone()["taken"] >= event["seats"]
            cur.execute(
                "DELETE FROM equipment_bookings WHERE user_id = %s AND event_id = %s;",
                (user_id, event_id),
            )
            cur.execute(
                "DELETE FROM registrations WHERE user_id = %s AND event_id = %s;",
                (user_id, event_id),
            )
            return "cancelled", was_full

    def create_saved_event(self, user_id: int, event_id: int) -> dict[str, Any]:
        sql = """
            INSERT INTO saved_events (user_id, event_id)
            VALUES (%s, %s)
            ON CONFLICT (user_id, event_id) DO NOTHING
            RETURNING id, user_id, event_id, created_at;
        """
        with get_cursor(self.conn_str) as cur:
            cur.execute(sql, (user_id, event_id))
            saved = cur.fetchone()
        # Saving twice is not an error: the event is simply already in the list
        return saved or self.get_saved_event(user_id, event_id)

    def delete_saved_event(self, user_id: int, event_id: int) -> bool:
        with get_cursor(self.conn_str) as cur:
            cur.execute(
                "DELETE FROM saved_events WHERE user_id = %s AND event_id = %s RETURNING id;",
                (user_id, event_id),
            )
            return cur.fetchone() is not None

    def get_saver_ids(self, event_id: int) -> list[int]:
        sql = "SELECT user_id FROM saved_events WHERE event_id = %s ORDER BY created_at ASC;"
        with get_cursor(self.conn_str) as cur:
            cur.execute(sql, (event_id,))
            return [row["user_id"] for row in cur.fetchall()]

    def create_notifications(
        self, user_ids: list[int], event_id: int, message: str
    ) -> list[dict[str, Any]]:
        if not user_ids:
            return []
        with get_cursor(self.conn_str) as cur:
            created = []
            for uid in user_ids:
                cur.execute(
                    """
                    INSERT INTO notifications (user_id, event_id, message)
                    VALUES (%s, %s, %s)
                    RETURNING id, user_id, event_id, message, created_at;
                    """,
                    (uid, event_id, message),
                )
                created.append(cur.fetchone())
            return created
