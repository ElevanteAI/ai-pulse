from app import models
from app.db import SessionLocal
from app.services.questions import questions_for
from tests.conftest import login


def dashboard(client):
    headers, _ = login(client, "asha@northwind.test", "Northwind Logistics")
    response = client.get("/dashboard", headers=headers)
    assert response.status_code == 200
    return response.json()


def complete(member, db, flags=None, score=3):
    db.query(models.Response).filter_by(membership_id=member.id).delete()
    for question in questions_for(member.job_role, member.seniority):
        db.add(models.Response(membership_id=member.id, question_id=question["id"], answer="Completed example", score=score, flags=flags or []))


def test_seed_shows_five_completers_and_hides_small_counts(client):
    data = dashboard(client)
    sales = next(d for d in data["departments"] if d["department"] == "Sales")
    assert sales["responded"] == 5
    assert sales["average_score"] == 4
    hidden = next(d for d in data["departments"] if d["hidden"])
    assert hidden == {"department": "Other teams", "hidden": True}
    assert data["top_risks"] == []
    assert "Support" not in str(data)


def test_four_completers_are_hidden_and_partial_fifth_does_not_count(client):
    with SessionLocal() as db:
        member = db.query(models.Membership).join(models.User).filter(models.User.email == "neha@northwind.test").one()
        db.query(models.Response).filter_by(membership_id=member.id, question_id="common-open").delete()
        db.commit()
    assert dashboard(client)["departments"] == [{"department": "Other teams", "hidden": True}]


def test_other_teams_requires_five_combined_completers(client):
    with SessionLocal() as db:
        members = db.query(models.Membership).filter(models.Membership.org_id == 1, models.Membership.department_id.in_([2, 3])).all()
        assert len(members) == 5
        first_member_id = members[0].id
        for member in members:
            complete(member, db, ["policy_unaware"])
        db.commit()
    other = next(d for d in dashboard(client)["departments"] if d["department"] == "Other teams")
    assert other["hidden"] is False
    assert other["responded"] == 5
    assert other["average_score"] == 3
    assert dashboard(client)["top_risks"]
    with SessionLocal() as db:
        db.query(models.Response).filter_by(membership_id=first_member_id).delete()
        db.commit()
    data = dashboard(client)
    assert next(d for d in data["departments"] if d["department"] == "Other teams") == {"department": "Other teams", "hidden": True}
    assert data["top_risks"] == []


def test_unscored_answers_still_complete_but_do_not_create_zero_average(client):
    with SessionLocal() as db:
        members = db.query(models.Membership).filter_by(org_id=1, department_id=1).all()
        for member in members:
            complete(member, db, score=None)
        db.commit()
    sales = next(d for d in dashboard(client)["departments"] if d["department"] == "Sales")
    assert sales["responded"] == 5
    assert sales["average_score"] is None
    assert sales["level"] == "Not assessed"
