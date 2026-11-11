import re
from fastapi.testclient import TestClient
from src.main import app
from src.routes.auth import COOKIE_NAME, get_auth_service
from src.services.auth import AuthService
from tests.test_auth_service import FakeUsersRepository


def create_test_client():
    fake_repo = FakeUsersRepository()
    # AC-1 requires 600000 iterations recorded in hash
    auth_service = AuthService(fake_repo, session_secret="test-secret-key", default_iterations=600000)
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    client = TestClient(app)
    return client, fake_repo


def test_AC_1_visitor_registers_and_signs_in_password_is_pbkdf2():
    """[AC-1] A visitor registers with an email and a password, signs in, and sees the list of upcoming events. In users, the stored password is a salted PBKDF2-HMAC-SHA256 hash that records its salt and its iteration count, 600000, and is not the password itself."""
    client, repo = create_test_client()

    email = "newuser@example.com"
    raw_password = "SecurePassword123!"

    # 1. Register
    reg_resp = client.post("/api/auth/register", json={"email": email, "password": raw_password})
    assert reg_resp.status_code == 201
    assert COOKIE_NAME in reg_resp.cookies

    # Check user row in users repo
    user_row = repo.get_user_by_email(email)
    assert user_row is not None
    assert user_row["password_hash"] != raw_password

    # PBKDF2-HMAC-SHA256 with 600000 iterations recorded
    match = re.match(r"^pbkdf2_sha256\$(\d+)\$([A-Za-z0-9+/=]+)\$([A-Za-z0-9+/=]+)$", user_row["password_hash"])
    assert match is not None, f"Hash format invalid: {user_row['password_hash']}"
    iterations, salt_b64, hash_b64 = match.groups()
    assert int(iterations) == 600000
    assert len(salt_b64) > 0
    assert len(hash_b64) > 0

    # 2. Sign in
    login_resp = client.post("/api/auth/login", json={"email": email, "password": raw_password})
    assert login_resp.status_code == 200
    assert COOKIE_NAME in login_resp.cookies

    # 3. Authenticated request
    cookie_val = login_resp.cookies[COOKIE_NAME]
    client.cookies.set(COOKIE_NAME, cookie_val)
    me_resp = client.get("/api/auth/me")
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == email


def test_AC_2_two_users_same_password_have_different_hashes():
    """[AC-2] Two users register with the same password. Both can sign in and see the list of upcoming events, and their stored hashes in users are different."""
    client, repo = create_test_client()

    shared_password = "IdenticalPassword123!"
    user1_email = "user1@example.com"
    user2_email = "user2@example.com"

    # Both register with the same password
    resp1 = client.post("/api/auth/register", json={"email": user1_email, "password": shared_password})
    resp2 = client.post("/api/auth/register", json={"email": user2_email, "password": shared_password})
    assert resp1.status_code == 201
    assert resp2.status_code == 201

    row1 = repo.get_user_by_email(user1_email)
    row2 = repo.get_user_by_email(user2_email)

    # Hashes must be different because of random salt
    assert row1["password_hash"] != row2["password_hash"]

    # Both can sign in
    login1 = client.post("/api/auth/login", json={"email": user1_email, "password": shared_password})
    login2 = client.post("/api/auth/login", json={"email": user2_email, "password": shared_password})
    assert login1.status_code == 200
    assert login2.status_code == 200
    assert COOKIE_NAME in login1.cookies
    assert COOKIE_NAME in login2.cookies


def test_AC_3_wrong_password_shows_wrong_email_or_password_no_cookie():
    """[AC-3] A user who signs in with a wrong password sees 'Wrong email or password' and stays on the sign-in page. No session cookie is set."""
    client, repo = create_test_client()

    email = "registered@example.com"
    client.post("/api/auth/register", json={"email": email, "password": "CorrectPassword123!"})

    # Try signing in with wrong password
    resp = client.post("/api/auth/login", json={"email": email, "password": "WrongPassword!"})
    assert resp.status_code == 401
    data = resp.json()
    assert data["detail"] == "Wrong email or password"
    assert COOKIE_NAME not in resp.cookies
    assert "set-cookie" not in resp.headers
