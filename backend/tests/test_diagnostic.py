from app import models
from app.db import SessionLocal
from tests.conftest import login
from tests.helpers import full_answers


def _priya(client):
    headers, _ = login(client, "priya@northwind.test", "Northwind Logistics")  # junior support
    return headers


def test_full_valid_submission_is_saved(client):
    h = _priya(client)
    answers = full_answers("support", "junior")
    r = client.post("/diagnostic/submit", json={"answers": answers}, headers=h)
    assert r.status_code == 200
    assert r.json()["saved"] == len(answers)


def test_duplicate_answers_are_rejected(client):
    """Original code: 20 copies of the top answer made a junior a 'Leader'."""
    h = _priya(client)
    answers = full_answers("support", "junior")
    answers += [answers[0]] * 19
    r = client.post("/diagnostic/submit", json={"answers": answers}, headers=h)
    assert r.status_code == 400
    assert client.get("/reports/me", headers=h).json()["level"] != "Leader"


def test_questions_for_another_role_are_rejected(client):
    h = _priya(client)
    answers = full_answers("support", "junior") + [{"question_id": "eng-arch", "answer": "I set the standards others follow"}]
    r = client.post("/diagnostic/submit", json={"answers": answers}, headers=h)
    assert r.status_code == 400
    assert "eng-arch" in r.json()["detail"]


def test_partial_submission_is_rejected(client):
    h = _priya(client)
    r = client.post("/diagnostic/submit", json={"answers": full_answers("support", "junior")[:2]}, headers=h)
    assert r.status_code == 400
    assert "Missing" in r.json()["detail"]


def test_invalid_mcq_option_is_rejected(client):
    h = _priya(client)
    answers = full_answers("support", "junior")
    answers[0]["answer"] = "Made-up option"
    assert client.post("/diagnostic/submit", json={"answers": answers}, headers=h).status_code == 400


def test_overlong_open_answer_is_rejected(client):
    h = _priya(client)
    answers = full_answers("support", "junior", open_text="x" * 5000)
    assert client.post("/diagnostic/submit", json={"answers": answers}, headers=h).status_code == 422


def test_retake_replaces_previous_answers(client):
    h = _priya(client)
    client.post("/diagnostic/submit", json={"answers": full_answers("support", "junior", mcq_choice=0)}, headers=h)
    client.post("/diagnostic/submit", json={"answers": full_answers("support", "junior", mcq_choice=-1)}, headers=h)
    db = SessionLocal()
    m = db.query(models.Membership).join(models.User).filter(models.User.email == "priya@northwind.test").one()
    rows = db.query(models.Response).filter_by(membership_id=m.id).all()
    assert len(rows) == len(full_answers("support", "junior"))  # not doubled
    assert client.get("/reports/me", headers=h).json()["answered"] == len(rows)


def test_rejected_submission_keeps_previous_result(client):
    h = _priya(client)
    client.post("/diagnostic/submit", json={"answers": full_answers("support", "junior")}, headers=h)
    before = client.get("/reports/me", headers=h).json()
    client.post("/diagnostic/submit", json={"answers": full_answers("support", "junior")[:1]}, headers=h)
    assert client.get("/reports/me", headers=h).json() == before


def test_lead_engineer_is_asked_senior_questions(client):
    headers, _ = login(client, "dev@northwind.test", "Northwind Logistics")
    got = {q["id"] for q in client.get("/diagnostic/questions", headers=headers).json()}
    assert {"eng-review", "eng-arch"} <= got


def test_scoring_points_are_not_sent_to_browser(client):
    h = _priya(client)
    for q in client.get("/diagnostic/questions", headers=h).json():
        assert "points" not in str(q)
