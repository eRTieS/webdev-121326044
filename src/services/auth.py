import base64
import hashlib
import hmac
import os
import re
from typing import Any
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

DEFAULT_ITERATIONS = 600000
DEFAULT_SALT_BYTES = 16


class AuthenticationError(Exception):
    pass


class ValidationError(Exception):
    pass


class UserAlreadyExistsError(Exception):
    pass


def hash_password(
    password: str,
    iterations: int = DEFAULT_ITERATIONS,
    salt: bytes | None = None,
) -> str:
    if salt is None:
        salt = os.urandom(DEFAULT_SALT_BYTES)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    salt_b64 = base64.b64encode(salt).decode("ascii")
    hash_b64 = base64.b64encode(derived).decode("ascii")
    return f"pbkdf2_sha256${iterations}${salt_b64}${hash_b64}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        parts = stored_hash.split("$")
        if len(parts) != 4:
            return False
        algo, iter_str, salt_b64, expected_hash_b64 = parts
        if algo != "pbkdf2_sha256":
            return False
        iterations = int(iter_str)
        salt = base64.b64decode(salt_b64.encode("ascii"))
        expected_hash = base64.b64decode(expected_hash_b64.encode("ascii"))
        computed_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, iterations
        )
        return hmac.compare_digest(computed_hash, expected_hash)
    except Exception:
        return False


class AuthService:
    def __init__(
        self,
        users_repo: Any,
        session_secret: str | None = None,
        default_iterations: int = DEFAULT_ITERATIONS,
    ):
        self.users_repo = users_repo
        self.session_secret = session_secret or os.environ.get("SESSION_SECRET")
        if not self.session_secret:
            raise RuntimeError("SESSION_SECRET is not set. Put it in .env or export it (see AGENTS.md).")
        self.default_iterations = default_iterations
        self.serializer = URLSafeTimedSerializer(self.session_secret)

    def validate_registration(self, email: str, password: str) -> None:
        if not email or "@" not in email or "." not in email.split("@")[-1]:
            raise ValidationError("Invalid email address")
        if not password or len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long")

    def register(
        self,
        email: str,
        password: str,
        role: str = "user",
        iterations: int | None = None,
    ) -> dict[str, Any]:
        self.validate_registration(email, password)
        clean_email = email.lower().strip()

        existing = self.users_repo.get_user_by_email(clean_email)
        if existing:
            raise UserAlreadyExistsError("An account with this email already exists")

        iters = iterations if iterations is not None else self.default_iterations
        pwd_hash = hash_password(password, iterations=iters)

        user = self.users_repo.create_user(
            email=clean_email,
            password_hash=pwd_hash,
            role=role,
            is_blocked=False,
        )
        return user

    def authenticate(self, email: str, password: str) -> dict[str, Any]:
        if not email or not password:
            raise AuthenticationError("Wrong email or password")

        clean_email = email.lower().strip()
        user = self.users_repo.get_user_by_email(clean_email)
        if not user:
            raise AuthenticationError("Wrong email or password")

        if not verify_password(password, user["password_hash"]):
            raise AuthenticationError("Wrong email or password")

        return user

    def create_session_token(self, user_id: int) -> str:
        return self.serializer.dumps({"user_id": user_id})

    def verify_session_token(self, token: str, max_age: int = 86400 * 7) -> int:
        try:
            data = self.serializer.loads(token, max_age=max_age)
            return data["user_id"]
        except (BadSignature, SignatureExpired, KeyError) as e:
            raise AuthenticationError("Invalid or expired session") from e

    def get_user_from_token(self, token: str) -> dict[str, Any]:
        user_id = self.verify_session_token(token)
        user = self.users_repo.get_user_by_id(user_id)
        if not user:
            raise AuthenticationError("Account no longer exists")
        return user
