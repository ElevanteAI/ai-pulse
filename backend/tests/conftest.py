import os
import pytest

os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["AI_MODE"] = "mock"
os.environ["PASSWORD_ITERATIONS"] = "1000"  # keep per-test seeding fast

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app import seed, ratelimit  # noqa: E402


@pytest.fixture()
def client():
    ratelimit.reset_all()
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
