from app.reset_password import main


def test_reset_password_cli(client, capsys):
    # unknown email lists accounts and fails
    assert main(["nobody@example.com", "--password", "whatever123"]) == 1
    assert "admin@example.com" in capsys.readouterr().out

    # too-short password is rejected
    assert main(["admin@example.com", "--password", "short"]) == 1

    # reset works and the new password logs in (old one doesn't)
    assert main(["ADMIN@example.com", "--password", "brand-new-pass"]) == 0
    assert client.post("/api/auth/login", json={"email": "admin@example.com",
                                                "password": "password123"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "admin@example.com",
                                                "password": "brand-new-pass"}).status_code == 200

    # put it back so other tests are unaffected
    assert main(["admin@example.com", "--password", "password123"]) == 0
    assert client.post("/api/auth/login", json={"email": "admin@example.com",
                                                "password": "password123"}).status_code == 200

    # listing with no email
    assert main([]) == 0
    assert "admin@example.com" in capsys.readouterr().out
