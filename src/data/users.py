from typing import Any
from src.data.db import get_cursor


class UsersRepository:
    def __init__(self, conn_str: str | None = None):
        self.conn_str = conn_str

    def create_user(
        self,
        email: str,
        password_hash: str,
        role: str = "user",
        is_blocked: bool = False,
        google_id: str | None = None,
    ) -> dict[str, Any]:
        sql = """
            INSERT INTO users (email, password_hash, role, is_blocked, google_id)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, email, password_hash, role, is_blocked, google_id, created_at;
        """
        with get_cursor(self.conn_str) as cur:
            cur.execute(sql, (email.lower().strip(), password_hash, role, is_blocked, google_id))
            return cur.fetchone()

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        sql = """
            SELECT id, email, password_hash, role, is_blocked, google_id, created_at
            FROM users
            WHERE email = %s;
        """
        with get_cursor(self.conn_str) as cur:
            cur.execute(sql, (email.lower().strip(),))
            return cur.fetchone()

    def get_user_by_id(self, user_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT id, email, password_hash, role, is_blocked, google_id, created_at
            FROM users
            WHERE id = %s;
        """
        with get_cursor(self.conn_str) as cur:
            cur.execute(sql, (user_id,))
            return cur.fetchone()
