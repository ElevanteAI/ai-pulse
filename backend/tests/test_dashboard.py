"""Dashboard numbers, checked against values worked out by hand from the seed data.

Seed (Northwind): Vikram/Sales answered 4 and 4 -> 4.0.  Priya/Support answered 2 and 3 -> 2.5.
Engineering and HR have no answers.
"""
from app import models
from app.db import SessionLocal
from app.utils import maturity_level
from tests.conftest import login


def dashboard(client, email="asha@northwind.test", org="Northwind Logistics"):
    headers, _ = login(client, email, org)
    return client.get("/dashboard", headers=headers).json()


def dept(data, name):
    return next(d for d in data["departments"] if d["department"] == name)


def test_average_is_per_respondent_not_divided_by_headcount(client):
    """Original: Sales = (4+4)/3 people = 2.67. Vikram is the only respondent and averages 4.0."""
    sales = dept(dashboard(client), "Sales")
    assert sales["employees"] == 3
    assert sales["respondents"] == 1
    assert sales["average_score"] == 4.0


def test_department_with_no_answers_is_not_assessed_not_beginner(client):
    eng = dept(dashboard(client), "Engineering")
    assert eng["average_score"] is None
    assert eng["level"] == "Not assessed"


def test_report_and_dashboard_agree_on_level(client):
    """Original: thresholds differed, so 3.6 was 'Practitioner' on the report and 'Leader' on the dashboard."""
    headers, _ = login(client, "vikram@northwind.test", "Northwind Logistics")
    report = client.get("/reports/me", headers=headers).json()
    assert dept(dashboard(client), "Sales")["level"] == report["level"]
    for avg, expected in [(1.9, "Beginner"), (2.0, "Exploring"), (3.6, "Practitioner"), (4.0, "Leader")]:
        assert maturity_level(avg) == expected


def test_person_with_more_answers_does_not_outweigh_others(client):
    db = SessionLocal()
    nw = db.query(models.Organization).filter_by(name="Northwind Logistics").one()
    eng = next(d for d in nw.departments if d.name == "Engineering")
    dev, sara = (db.query(models.Membership).filter_by(org_id=nw.id, department_id=eng.id).order_by(models.Membership.id).all())
    for i in range(8):
        db.add(models.Response(membership_id=dev.id, question_id=f"q{i}", answer="x", score=5))
    db.add(models.Response(membership_id=sara.id, question_id="q0", answer="x", score=1))
    db.commit()
    # Per person: Dev 5.0, Sara 1.0 -> 3.0. A flat average over answers would give 41/9 = 4.56.
    assert dept(dashboard(client), "Engineering")["average_score"] == 3.0


def test_risks_count_people_not_answers(client):
    db = SessionLocal()
    priya = db.query(models.Membership).join(models.User).filter(models.User.email == "priya@northwind.test").one()
    for _ in range(3):
        db.add(models.Response(membership_id=priya.id, question_id="x", answer="x", score=3, flags=["customer_data_shared"]))
    db.commit()
    risks = {r["risk"]: r["people"] for r in dashboard(client)["top_risks"]}
    assert risks["customer_data_shared"] == 1


def test_needs_review_answers_are_excluded_and_reported(client):
    db = SessionLocal()
    vikram = db.query(models.Membership).join(models.User).filter(models.User.email == "vikram@northwind.test").one()
    db.add(models.Response(membership_id=vikram.id, question_id="x", answer="x", score=None, ai_status="needs_review"))
    db.commit()
    data = dashboard(client)
    assert dept(data, "Sales")["average_score"] == 4.0
    assert data["ai_scoring"]["needs_review"] == 1
