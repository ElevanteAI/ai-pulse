import os
import pytest
import bcrypt

os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["AI_MODE"] = "mock"
os.environ["DEV_MODE"] = "true"

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app import seed  # noqa: E402


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(seed, "hash_password", lambda password: bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=4)).decode())
    seed.run()
    return TestClient(app)


def login(client, email, org_name=None):
    r = client.post("/auth/login", json={"email": email, "password": "pulse123"})
    data = r.json()
    token = data["token"]
    if org_name:
        org = next(o for o in data["organizations"] if o["org_name"] == org_name)
        token = client.post("/auth/select-org", json={"org_id": org["org_id"]},
                            headers={"Authorization": f"Bearer {token}"}).json()["token"]
    return {"Authorization": f"Bearer {token}"}, data
