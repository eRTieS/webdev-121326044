import time
import pytest
from itsdangerous import URLSafeTimedSerializer
from src.services.auth import (
    AuthService,
    AuthenticationError,
    UserAlreadyExistsError,
    ValidationError,
    hash_password,
    verify_password,
)


class FakeUsersRepository:
    def __init__(self):
        self.users = {}
        self._next_id = 1

    def create_user(
        self,
        email: str,
        password_hash: str,
        role: str = "user",
        is_blocked: bool = False,
        google_id: str | None = None,
    ):
        user = {
            "id": self._next_id,
            "email": email,
            "password_hash": password_hash,
            "role": role,
            "is_blocked": is_blocked,
            "google_id": google_id,
            "created_at": "2026-11-10T12:00:00Z",
        }
        self.users[self._next_id] = user
        self._next_id += 1
        return user

    def get_user_by_email(self, email: str):
        for user in self.users.values():
            if user["email"] == email:
                return user
        return None

    def get_user_by_id(self, user_id: int):
        return self.users.get(user_id)


def test_hash_password_and_verify_password():
    # Use 1000 iterations for test speed
    h = hash_password("secret123", iterations=1000)
    assert h.startswith("pbkdf2_sha256$1000$")
    assert verify_password("secret123", h) is True
    assert verify_password("wrongpass", h) is False


def test_hash_password_with_custom_salt():
    salt = b"0123456789abcdef"
    h1 = hash_password("secret123", iterations=1000, salt=salt)
    h2 = hash_password("secret123", iterations=1000, salt=salt)
    assert h1 == h2


def test_verify_password_invalid_formats():
    assert verify_password("pass", "invalid_format") is False
    assert verify_password("pass", "sha256$1000$salt$hash") is False
    assert verify_password("pass", "pbkdf2_sha256$not_a_number$salt$hash") is False
    assert verify_password("pass", "pbkdf2_sha256$1000$bad_b64$bad_b64") is False


def test_auth_service_refuses_to_start_without_session_secret(monkeypatch):
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    with pytest.raises(RuntimeError, match="SESSION_SECRET is not set"):
        AuthService(FakeUsersRepository())


def test_validate_registration_errors():
    service = AuthService(FakeUsersRepository(), default_iterations=1000)
    with pytest.raises(ValidationError, match="Invalid email"):
        service.validate_registration("", "password123")
    with pytest.raises(ValidationError, match="Invalid email"):
        service.validate_registration("notanemail", "password123")
    with pytest.raises(ValidationError, match="Invalid email"):
        service.validate_registration("user@nodot", "password123")
    with pytest.raises(ValidationError, match="Password must be at least 8 characters"):
        service.validate_registration("user@example.com", "short")
    with pytest.raises(ValidationError, match="Password must be at least 8 characters"):
        service.validate_registration("user@example.com", "")


def test_register_and_duplicate():
    repo = FakeUsersRepository()
    service = AuthService(repo, default_iterations=1000)

    user = service.register("Student@Example.COM", "password123")
    assert user["id"] == 1
    assert user["email"] == "student@example.com"
    assert user["role"] == "user"
    assert user["is_blocked"] is False

    with pytest.raises(UserAlreadyExistsError, match="already exists"):
        service.register("student@example.com", "anotherpassword")


def test_authenticate_success_and_failure():
    repo = FakeUsersRepository()
    service = AuthService(repo, default_iterations=1000)

    service.register("test@example.com", "correctpassword123")

    with pytest.raises(AuthenticationError, match="Wrong email or password"):
        service.authenticate("", "pass")
    with pytest.raises(AuthenticationError, match="Wrong email or password"):
        service.authenticate("test@example.com", "")
    with pytest.raises(AuthenticationError, match="Wrong email or password"):
        service.authenticate("unknown@example.com", "correctpassword123")
    with pytest.raises(AuthenticationError, match="Wrong email or password"):
        service.authenticate("test@example.com", "wrongpass")

    authenticated = service.authenticate("TEST@example.com", "correctpassword123")
    assert authenticated["email"] == "test@example.com"


def test_session_token_and_get_user():
    repo = FakeUsersRepository()
    service = AuthService(repo, session_secret="test-secret", default_iterations=1000)

    user = service.register("user@example.com", "password123")
    token = service.create_session_token(user["id"])

    retrieved = service.get_user_from_token(token)
    assert retrieved["id"] == user["id"]
    assert retrieved["email"] == "user@example.com"

    # Bad signature
    with pytest.raises(AuthenticationError, match="Invalid or expired session"):
        service.get_user_from_token("bad.token.signature")

    # Expired token
    expired_serializer = URLSafeTimedSerializer("test-secret")
    expired_token = expired_serializer.dumps({"user_id": user["id"]})
    with pytest.raises(AuthenticationError, match="Invalid or expired session"):
        service.verify_session_token(expired_token, max_age=-1)

    # Malformed payload missing user_id
    bad_payload_token = expired_serializer.dumps({"wrong_key": 123})
    with pytest.raises(AuthenticationError, match="Invalid or expired session"):
        service.verify_session_token(bad_payload_token)

    # User no longer in DB
    del repo.users[user["id"]]
    with pytest.raises(AuthenticationError, match="Account no longer exists"):
        service.get_user_from_token(token)
