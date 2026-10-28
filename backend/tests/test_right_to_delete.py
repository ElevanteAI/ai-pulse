"""Client request #2: an employee can delete all their answers and their report themselves,
and it disappears from every dashboard immediately."""
from app import models
from app.db import SessionLocal
from tests.conftest import login
from tests.helpers import full_answers


def admin_dashboard(client):
    headers, _ = login(client, "asha@northwind.test", "Northwind Logistics")
    return client.get("/dashboard", headers=headers).json()


def rows_for(email, org_name):
    db = SessionLocal()
    return (db.query(models.Response).join(models.Membership).join(models.User).join(models.Organization)
            .filter(models.User.email == email, models.Organization.name == org_name).count())


def test_employee_deletes_own_answers_and_report(client):
    h, _ = login(client, "vikram@northwind.test", "Northwind Logistics")
    assert client.get("/reports/me", headers=h).json()["answered"] > 0

    r = client.delete("/reports/me", headers=h)
    assert r.status_code == 200 and r.json()["deleted_answers"] == 7

    report = client.get("/reports/me", headers=h).json()
    assert report["answered"] == 0 and report["level"] == "Not assessed"
    assert report["risks"] == [] and report["ai_assessments"] == []
    assert rows_for("vikram@northwind.test", "Northwind Logistics") == 0  # really gone, not flagged


def test_deletion_removes_person_from_dashboard_immediately(client):
    before = admin_dashboard(client)
    sales = next(g for g in before["groups"] if g["department"] == "Sales")
    assert sales["respondents"] == 5

    h, _ = login(client, "vikram@northwind.test", "Northwind Logistics")
    client.delete("/reports/me", headers=h)

    after = admin_dashboard(client)
    # Sales drops to 4, so it is no longer shown on its own at all
    assert "Sales" not in [g["department"] for g in after["groups"]]
    assert after["overall"]["respondents"] == sum(g["respondents"] for g in after["groups"])


def test_deletion_only_affects_the_selected_org(client):
    db = SessionLocal()
    ravi_bp = (db.query(models.Membership).join(models.User).join(models.Organization)
               .filter(models.User.email == "ravi@consult.test", models.Organization.name == "Bluepeak Retail").one())
    db.add(models.Response(membership_id=ravi_bp.id, question_id="common-freq", answer="Daily", score=4))
    db.commit()

    h, _ = login(client, "ravi@consult.test", "Northwind Logistics")
    client.delete("/reports/me", headers=h)
    assert rows_for("ravi@consult.test", "Northwind Logistics") == 0
    assert rows_for("ravi@consult.test", "Bluepeak Retail") == 1


def test_deletion_does_not_touch_colleagues(client):
    before = rows_for("neha@northwind.test", "Northwind Logistics")
    h, _ = login(client, "vikram@northwind.test", "Northwind Logistics")
    client.delete("/reports/me", headers=h)
    assert rows_for("neha@northwind.test", "Northwind Logistics") == before


def test_delete_requires_login_and_org(client):
    assert client.delete("/reports/me").status_code == 401
    h, _ = login(client, "vikram@northwind.test")  # no org selected
    assert client.delete("/reports/me", headers=h).status_code == 400


def test_can_retake_after_deleting(client):
    h, _ = login(client, "priya@northwind.test", "Northwind Logistics")
    client.delete("/reports/me", headers=h)
    r = client.post("/diagnostic/submit", json={"answers": full_answers("support", "junior")}, headers=h)
    assert r.status_code == 200
    assert client.get("/reports/me", headers=h).json()["answered"] == 6


def test_deleting_twice_is_harmless(client):
    h, _ = login(client, "vikram@northwind.test", "Northwind Logistics")
    client.delete("/reports/me", headers=h)
    r = client.delete("/reports/me", headers=h)
    assert r.status_code == 200 and r.json()["deleted_answers"] == 0
