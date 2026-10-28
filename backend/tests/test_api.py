from app import models
from app.db import SessionLocal
from tests.conftest import login


def add_completed_assessment(membership_id, score=3, flags=None):
    db = SessionLocal()
    assessment = models.Assessment(membership_id=membership_id, status="completed")
    db.add(assessment)
    db.flush()
    db.add(models.Response(assessment_id=assessment.id, membership_id=membership_id,
                           question_id="common-freq", answer="A few times a week",
                           score=score, flags=flags or []))
    db.commit()
    db.close()


def test_login_lists_organizations(client):
    _, data = login(client, "ravi@consult.test")
    names = {o["org_name"] for o in data["organizations"]}
    assert names == {"Northwind Logistics", "Bluepeak Retail"}


def test_employee_sees_questions(client):
    headers, _ = login(client, "priya@northwind.test", "Northwind Logistics")
    r = client.get("/diagnostic/questions", headers=headers)
    assert r.status_code == 200
    assert any(q["id"] == "sup-drafts" for q in r.json())


def test_admin_dashboard(client):
    headers, _ = login(client, "asha@northwind.test", "Northwind Logistics")
    r = client.get("/dashboard", headers=headers)
    assert r.status_code == 200
    assert r.json()["departments"] == []


def test_admin_cannot_see_other_org(client):
    headers, _ = login(client, "ravi@consult.test", "Bluepeak Retail")
    r = client.get("/dashboard?org_id=1", headers=headers)
    assert r.status_code == 200
    assert r.json()["organization"] == "Bluepeak Retail"


def test_user_cannot_select_an_organization_they_do_not_belong_to(client):
    headers, _ = login(client, "priya@northwind.test")
    r = client.post("/auth/select-org", json={"org_id": 2}, headers=headers)
    assert r.status_code == 403


def test_employee_cannot_submit_a_question_assigned_to_another_role(client):
    headers, _ = login(client, "priya@northwind.test", "Northwind Logistics")
    r = client.post("/diagnostic/submit", headers=headers,
                    json={"answers": [{"question_id": "eng-arch", "answer": "No"}]})
    assert r.status_code == 400


def test_small_departments_are_only_shown_as_safe_aggregate(client):
    db = SessionLocal()
    memberships = db.query(models.Membership).filter_by(org_id=1, role="employee").limit(5).all()
    db.close()
    for membership in memberships:
        add_completed_assessment(membership.id, flags=["policy_unaware"])
    headers, _ = login(client, "asha@northwind.test", "Northwind Logistics")
    r = client.get("/dashboard", headers=headers)
    assert r.status_code == 200
    assert [item["department"] for item in r.json()["departments"]] == ["Other teams"]
    assert r.json()["top_risks"] == [["policy_unaware", 5]]


def test_employee_can_delete_all_their_diagnostic_data(client):
    db = SessionLocal()
    membership = db.query(models.Membership).filter_by(user_id=5, org_id=1).first()
    db.close()
    add_completed_assessment(membership.id)
    headers, _ = login(client, "priya@northwind.test", "Northwind Logistics")
    assert client.get("/reports/me", headers=headers).json()["answered"] == 1
    assert client.delete("/reports/me", headers=headers).status_code == 204
    report = client.get("/reports/me", headers=headers).json()
    assert report["answered"] == 0
    assert report["level"] == "Not assessed"
    assert report["pulse_practice"] == []


def test_report_includes_pulse_practice_recommendations(client):
    db = SessionLocal()
    membership = db.query(models.Membership).filter_by(user_id=5, org_id=1).first()
    db.close()
    add_completed_assessment(membership.id, score=2, flags=["customer_data_shared"])
    headers, _ = login(client, "priya@northwind.test", "Northwind Logistics")
    report = client.get("/reports/me", headers=headers).json()
    assert "pulse_practice" in report
    assert len(report["pulse_practice"]) > 0
    first = report["pulse_practice"][0]
    assert "practice" in first
    assert "success_measure" in first
    assert first["url"].startswith("https://")
    assert first["topic"] == "data_safety"

