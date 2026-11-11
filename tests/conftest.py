import pytest
from dotenv import load_dotenv

# TEST_DATABASE_URL for the data-layer tests comes from .env
load_dotenv()


@pytest.fixture(autouse=True)
def test_settings(monkeypatch):
    # Tests sign their own session tokens and never see the real secret
    monkeypatch.setenv("SESSION_SECRET", "test-session-secret")
    yield
    from src.main import app

    app.dependency_overrides.clear()
