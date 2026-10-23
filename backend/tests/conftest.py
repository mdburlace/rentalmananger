import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="rm-test-")
os.environ["RM_DATA_DIR"] = _tmp
os.environ["RM_SECRET_KEY"] = "test-secret-key-that-is-long-enough-for-hs256"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import create_app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(create_app()) as c:
        r = c.post("/api/auth/setup", json={"portfolio_name": "Test Portfolio", "name": "Admin",
                                            "email": "admin@example.com", "password": "password123"})
        assert r.status_code == 200, r.text
        yield c


@pytest.fixture(scope="session")
def owners(client):
    a = client.post("/api/owners", json={"name": "Owner A"}).json()
    b = client.post("/api/owners", json={"name": "Owner B"}).json()
    return a, b


@pytest.fixture(scope="session")
def prop(client, owners):
    a, b = owners
    r = client.post("/api/properties", json={
        "name": "Test St", "address_line": "1 Test St", "suburb": "Brisbane", "state": "QLD", "postcode": "4000",
        "ownerships": [{"owner_id": a["id"], "share_percent": 50}, {"owner_id": b["id"], "share_percent": 50}],
    })
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture(scope="session")
def cats(client):
    return {c["ato_key"] + ":" + c["name"]: c for c in client.get("/api/categories").json()}


def cat_id(cats, name):
    return next(c["id"] for c in cats.values() if c["name"] == name)
