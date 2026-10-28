import os
import pytest

os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["AI_MODE"] = "mock"

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app import seed  # noqa: E402


@pytest.fixture()
def client():
    seed.run()
    return TestClient(app)


def login(client, email, org_name=None):
    r = client.post("/auth/login", json={"email": email, "password": "pulse123"})
    data = r.json()
    
    # TestClient automatically handles cookies, so no need to manually extract token
    # The cookie is stored in client.cookies and will be sent with subsequent requests
    
    if org_name:
        org = next(o for o in data["organizations"] if o["org_name"] == org_name)
        # select-org also sets the cookie automatically
        # But we want to preserve the organizations list from the login response
        r = client.post("/auth/select-org", json={"org_id": org["org_id"]})
    
    # Return empty dict for headers - TestClient handles cookies automatically
    return {}, data


