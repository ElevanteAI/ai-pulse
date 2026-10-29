import pytest
from sqlalchemy.exc import IntegrityError

from app import models
from app.db import SessionLocal
from app.utils import maturity_level
from app.routes.dashboard import department_statistics
from app.services.questions import questions_for
from tests.conftest import login


def test_dashboard_weights_people_equally(client):
    with SessionLocal() as db:
        db.query(models.Response).delete()
        members = db.query(models.Membership).join(models.User).filter(models.User.email.in_(["priya@northwind.test", "arjun@northwind.test"])).all()
        for member in members:
            score = 1 if member.seniority == "junior" else 4
            for question in questions_for(member.job_role, member.seniority):
                db.add(models.Response(membership_id=member.id, question_id=question["id"], answer="Example", score=score))
        db.commit()
        statistics, _ = department_statistics(members, db)
        assert statistics["average_score"] == 2.5
        empty, _ = department_statistics([], db)
        assert empty["average_score"] is None
        assert empty["level"] == "Not assessed"


@pytest.mark.parametrize("score,level", [(None, "Not assessed"), (1.99, "Beginner"), (2, "Exploring"), (3, "Practitioner"), (4, "Leader")])
def test_shared_maturity_thresholds(score, level):
    assert maturity_level(score) == level


def test_resubmit_replaces_response(client):
    headers, _ = login(client, "priya@northwind.test", "Northwind Logistics")
    for answer in ["Daily", "Never"]:
        response = client.post("/diagnostic/submit", headers=headers, json={"answers": [{"question_id": "common-freq", "answer": answer}]})
        assert response.status_code == 200
    with SessionLocal() as db:
        member = db.query(models.Membership).join(models.User).filter(models.User.email == "priya@northwind.test").one()
        rows = db.query(models.Response).filter_by(membership_id=member.id, question_id="common-freq").all()
        assert len(rows) == 1
        assert rows[0].score == 1
        db.add(models.Response(membership_id=member.id, question_id="common-freq", answer="Daily", score=4))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


@pytest.mark.parametrize("question_id", ["eng-assistant", "sup-escalation", "unknown"])
def test_submit_rejects_unassigned_questions(client, question_id):
    headers, _ = login(client, "priya@northwind.test", "Northwind Logistics")
    response = client.post("/diagnostic/submit", headers=headers, json={"answers": [{"question_id": question_id, "answer": "No"}]})
    assert response.status_code == 400


def test_invalid_submission_saves_nothing(client):
    headers, _ = login(client, "sara@northwind.test", "Northwind Logistics")
    response = client.post("/diagnostic/submit", headers=headers, json={"answers": [{"question_id": "common-freq", "answer": "Daily"}, {"question_id": "common-policy", "answer": "invalid"}]})
    assert response.status_code == 400
    assert client.get("/reports/me", headers=headers).json()["answered"] == 0


def test_submit_rejects_repeated_question_in_payload(client):
    headers, _ = login(client, "neha@northwind.test", "Northwind Logistics")
    answer = {"question_id": "common-freq", "answer": "Daily"}
    assert client.post("/diagnostic/submit", headers=headers, json={"answers": [answer, answer]}).status_code == 400
