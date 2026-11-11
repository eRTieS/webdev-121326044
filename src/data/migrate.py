"""Applies the numbered SQL files in migrations/ that have not run yet.

Run it with `python -m src.data.migrate`. Each file runs once; its name is recorded
in schema_migrations, so a migration that has run is never edited, only followed
by a new one.
"""
from pathlib import Path

from src.data.db import get_connection

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


def migrate(conn_str: str | None = None) -> list[str]:
    applied = []
    with get_connection(conn_str) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                name TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )
        done = {row["name"] for row in conn.execute("SELECT name FROM schema_migrations;")}
        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if path.name in done:
                continue
            conn.execute(path.read_text(encoding="utf-8"))
            conn.execute("INSERT INTO schema_migrations (name) VALUES (%s);", (path.name,))
            applied.append(path.name)
        conn.commit()
    return applied


if __name__ == "__main__":  # pragma: no cover
    from dotenv import load_dotenv

    load_dotenv()
    names = migrate()
    print("Applied: " + ", ".join(names) if names else "Nothing to apply.")
