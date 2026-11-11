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
            SELECT id, status, seats, start_time, reservation_open, reservation_close
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

    def create_registration_if_seat_free(
        self, user_id: int, event_id: int
    ) -> tuple[str, dict[str, Any] | None]:
        """Returns ("created", row), ("duplicate", row), ("full", None) or ("missing", None).

        The seat count is checked here, not in the service, because only a locked
        event row stops two people from taking the last seat at the same time.
        """
        with get_cursor(self.conn_str) as cur:
            cur.execute("SELECT seats FROM events WHERE id = %s FOR UPDATE;", (event_id,))
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
            return "created", cur.fetchone()

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
