from app import models
from app.db import SessionLocal
from tests.conftest import login
from tests.test_privacy import dashboard


def test_deletion_empties_report_and_hides_department_immediately(client):
    headers, _ = login(client, "neha@northwind.test", "Northwind Logistics")
    assert any(d["department"] == "Sales" for d in dashboard(client)["departments"])
    response = client.delete("/reports/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["deleted"] > 0
    report = client.get("/reports/me", headers=headers).json()
    assert report["answered"] == 0
    assert report["average_score"] is None
    assert report["level"] == "Not assessed"
    assert report["risks"] == []
    assert dashboard(client)["departments"] == [{"department": "Other teams", "hidden": True}]
    assert client.delete("/reports/me", headers=headers).json() == {"deleted": 0}


def test_deletion_is_scoped_to_membership_and_preserves_other_people(client):
    headers, _ = login(client, "ravi@consult.test", "Northwind Logistics")
    with SessionLocal() as db:
        user = db.query(models.User).filter_by(email="ravi@consult.test").one()
        memberships = db.query(models.Membership).filter_by(user_id=user.id).all()
        for member in memberships:
            db.add(models.Response(membership_id=member.id, question_id="common-freq", answer="Daily", score=4))
        db.commit()
        total_before = db.query(models.Response).count()
    assert client.delete("/reports/me", headers=headers).json() == {"deleted": 1}
    other_headers, _ = login(client, "ravi@consult.test", "Bluepeak Retail")
    assert client.get("/reports/me", headers=other_headers).json()["answered"] == 1
    with SessionLocal() as db:
        assert db.query(models.Response).count() == total_before - 1


def test_deletion_requires_selected_membership(client):
    assert client.delete("/reports/me").status_code == 401
    headers, _ = login(client, "neha@northwind.test")
    assert client.delete("/reports/me", headers=headers).status_code == 400
