import re

import pytest

from app.config import get_settings
from app.routers import auth as auth_router


@pytest.fixture
def outbox(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(s, "smtp_from", "rental@example.com")
    monkeypatch.setattr(s, "public_url", "https://rent.example.com")
    auth_router._last_reset_request.clear()
    sent = []
    monkeypatch.setattr(auth_router.mailer, "send_email_logged", lambda to, subject, body: sent.append((to, body)))
    return sent


def _token(body):
    m = re.search(r"https://rent\.example\.com/reset-password\?token=(\S+)", body)
    assert m, body
    return m.group(1)


def test_forgot_disabled_without_smtp(client):
    assert client.get("/api/auth/status").json()["email_reset"] is False
    assert client.post("/api/auth/forgot-password", json={"email": "admin@example.com"}).status_code == 503


def test_email_reset_flow(client, outbox):
    assert client.get("/api/auth/status").json()["email_reset"] is True

    # unknown email: same response, no mail
    r = client.post("/api/auth/forgot-password", json={"email": "nobody@example.com"})
    assert r.status_code == 200 and outbox == []

    r = client.post("/api/auth/forgot-password", json={"email": "Admin@Example.com"})
    assert r.status_code == 200 and len(outbox) == 1
    assert outbox[0][0] == "admin@example.com"
    token = _token(outbox[0][1])

    # cooldown: a second request straight away sends nothing
    client.post("/api/auth/forgot-password", json={"email": "admin@example.com"})
    assert len(outbox) == 1

    # the reset token can't be used as a session
    assert client.get("/api/auth/me", headers={"authorization": f"Bearer {token}"},
                      cookies={"rm_session": ""}).status_code == 401

    # bad token / short password rejected
    assert client.post("/api/auth/reset-password", json={"token": "x" * 20, "new_password": "whatever123"}).status_code == 400
    assert client.post("/api/auth/reset-password", json={"token": token, "new_password": "short"}).status_code == 422

    r = client.post("/api/auth/reset-password", json={"token": token, "new_password": "emailed-new-pass"})
    assert r.status_code == 200, r.text
    assert client.post("/api/auth/login", json={"email": "admin@example.com", "password": "emailed-new-pass"}).status_code == 200

    # link is single-use
    assert client.post("/api/auth/reset-password", json={"token": token, "new_password": "another-pass1"}).status_code == 400

    # restore the original password for other tests
    auth_router._last_reset_request.clear()
    client.post("/api/auth/forgot-password", json={"email": "admin@example.com"})
    token2 = _token(outbox[-1][1])
    assert client.post("/api/auth/reset-password", json={"token": token2, "new_password": "password123"}).status_code == 200
    assert client.post("/api/auth/login", json={"email": "admin@example.com", "password": "password123"}).status_code == 200
