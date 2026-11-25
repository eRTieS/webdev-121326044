import os
import pytest
from dotenv import load_dotenv
from src.data.db import get_cursor
from src.data.migrate import migrate
from src.data.seed import seed

# TEST_DATABASE_URL for the data-layer tests comes from .env
load_dotenv()

TEST_DB = os.environ.get("TEST_DATABASE_URL")
ORIG_DB = os.environ.get("DATABASE_URL")


@pytest.fixture(autouse=True)
def test_settings(monkeypatch):
    # Tests sign their own session tokens and never see the real secret
    monkeypatch.setenv("SESSION_SECRET", "test-session-secret")
    yield
    from src.main import app

    app.dependency_overrides.clear()


@pytest.fixture
def passwords(monkeypatch):
    if not TEST_DB:
        pytest.skip("TEST_DATABASE_URL is not set")
    if TEST_DB == ORIG_DB:
        pytest.fail("TEST_DATABASE_URL is the development database; these tests would wipe it")
    with get_cursor(TEST_DB) as cur:
        cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    migrate(TEST_DB)
    pwds = seed(TEST_DB, iterations=1000)
    monkeypatch.setenv("DATABASE_URL", TEST_DB)
    return pwds
