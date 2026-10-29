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
    token = data["token"]
    if org_name:
        org = next(o for o in data["organizations"] if o["org_name"] == org_name)
        token = client.post("/auth/select-org", json={"org_id": org["org_id"]},
                            headers={"Authorization": f"Bearer {token}"}).json()["token"]
    return {"Authorization": f"Bearer {token}"}, data


def add_respondents(dept_name, n, org_id=1, score=4, flags=None):
    """Create n extra employees in a department, each with one scored answer."""
    from app import models
    from app.db import SessionLocal
    db = SessionLocal()
    dept = db.query(models.Department).filter_by(org_id=org_id, name=dept_name).one()
    for i in range(n):
        u = models.User(name=f"Extra {dept_name} {i}", email=f"extra{dept_name}{i}@x.test", password_hash="x")
        db.add(u)
        db.flush()
        m = models.Membership(user_id=u.id, org_id=org_id, department_id=dept.id,
                              role="employee", job_role="support", seniority="mid")
        db.add(m)
        db.flush()
        db.add(models.Response(membership_id=m.id, question_id="common-freq", answer="Daily",
                               score=score, flags=flags or []))
    db.commit()
    db.close()
