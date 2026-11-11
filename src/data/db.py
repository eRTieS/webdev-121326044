import os
from contextlib import contextmanager
import psycopg
from psycopg.rows import dict_row


def database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set. Put it in .env or export it (see AGENTS.md).")
    return url


def get_connection(conn_str: str | None = None):
    return psycopg.connect(conn_str or database_url(), row_factory=dict_row)


@contextmanager
def get_cursor(conn_str: str | None = None):
    with get_connection(conn_str) as conn:
        with conn.cursor() as cur:
            yield cur
        conn.commit()
