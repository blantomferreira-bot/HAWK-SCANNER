import os

os.environ.setdefault("JWT_SECRET", "test-secret-that-is-at-least-thirty-two-characters-long")

from src.application.security import create_token, decode_access_token, hash_password, verify_password


def test_password_hash_round_trip():
    password_hash = hash_password("a-strong-password")
    assert verify_password("a-strong-password", password_hash)
    assert not verify_password("other-password", password_hash)


def test_access_token_round_trip():
    token = create_token("user-123", "USER", "access")
    assert decode_access_token(token) == {"id": "user-123", "role": "USER"}
