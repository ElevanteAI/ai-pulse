"""Cross-cutting checks: tenant blocking, malformed AI output via the API, and delete cascade."""
import pytest

from app.services import scoring
from tests.conftest import login
from tests.test_api import _add_respondents, _dashboard


def _open_answer_body(client, headers):
    qs = client.get("/diagnostic/questions", headers=headers).json()
    return {"answers": [
        {"question_id": q["id"], "answer": q["options"][0] if q["type"] == "mcq" else "I used AI to draft emails and checked them."}
        for q in qs
    ]}


# --- multi-tenant blocking -------------------------------------------------

def test_employee_cannot_open_dashboard(client):
    headers, data = login(client, "priya@northwind.test", "Northwind Logistics")
    r = client.get(f"/dashboard?org_id={data['organizations'][0]['org_id']}", headers=headers)
    assert r.status_code == 403


def test_dashboard_requires_token(client):
    assert client.get("/dashboard?org_id=1").status_code == 401


def test_cannot_mint_token_for_foreign_org_then_use_it(client):
    headers, _ = login(client, "asha@northwind.test", "Northwind Logistics")
    assert client.post("/auth/select-org", json={"org_id": 2}, headers=headers).status_code == 403
    assert client.post("/auth/select-org", json={"org_id": 9999}, headers=headers).status_code == 403


def test_multi_org_user_is_scoped_to_chosen_org(client):
    """Ravi is admin at Bluepeak but only an employee at Northwind."""
    nw, _ = login(client, "ravi@consult.test", "Northwind Logistics")
    bp, bp_data = login(client, "ravi@consult.test", "Bluepeak Retail")
    nw_id = next(o["org_id"] for o in client.post("/auth/login", json={"email": "ravi@consult.test", "password": "pulse123"}).json()["organizations"] if o["org_name"] == "Northwind Logistics")
    bp_id = next(o["org_id"] for o in bp_data["organizations"] if o["org_name"] == "Bluepeak Retail")
    assert client.get(f"/dashboard?org_id={bp_id}", headers=bp).status_code == 200
    assert client.get(f"/dashboard?org_id={nw_id}", headers=bp).status_code == 403  # token is for Bluepeak
    assert client.get(f"/dashboard?org_id={nw_id}", headers=nw).status_code == 403  # employee there


# --- malformed AI responses through the real endpoint -----------------------

@pytest.mark.parametrize("raw", [
    "not json at all",
    '```json\n{"score": 9, "reason": "x", "flags": ["invented"]}\n```',
    '{"score": "four"}',
    "",
])
def test_submit_survives_malformed_model_output(client, monkeypatch, raw):
    monkeypatch.setattr(scoring.llm, "score_answer", lambda q, a: raw)
    headers, _ = login(client, "priya@northwind.test", "Northwind Logistics")
    r = client.post("/diagnostic/submit", json=_open_answer_body(client, headers), headers=headers)
    assert r.status_code == 200
    report = client.get("/reports/me", headers=headers).json()
    assert 1 <= report["average_score"] <= 5
    assert set(report["risks"]) <= {"customer_data_shared", "confidential_data_shared", "unreviewed_output", "policy_unaware"}


def test_submit_survives_llm_timeout(client, monkeypatch):
    def boom(q, a):
        raise TimeoutError("slow")
    monkeypatch.setattr(scoring.llm, "score_answer", boom)
    headers, _ = login(client, "priya@northwind.test", "Northwind Logistics")
    assert client.post("/diagnostic/submit", json=_open_answer_body(client, headers), headers=headers).status_code == 200


# --- privacy grouping boundary ---------------------------------------------

def test_four_respondents_hidden_five_visible(client):
    _add_respondents("Northwind Logistics", "Engineering", 2)  # + Dev/Sara not seeded with answers => 2
    assert "Engineering" not in {r["department"] for r in _dashboard(client)["departments"]}
    _add_respondents("Northwind Logistics", "HR", 5)
    assert "HR" in {r["department"] for r in _dashboard(client)["departments"]}


# --- delete cascade ----------------------------------------------------------

def test_deleting_removes_risk_from_dashboard_and_report(client):
    _add_respondents("Northwind Logistics", "Sales", 5, flag="policy_unaware")
    assert "policy_unaware" in dict(_dashboard(client)["top_risks"])

    # a flagged respondent removes their own data; the risk count must drop by exactly one
    from app.db import SessionLocal
    from app import models
    from app.auth import hash_password
    db = SessionLocal()
    u = db.query(models.User).filter_by(email="extraSales0@x.test").one()
    u.password_hash = hash_password("pulse123")
    db.commit()
    db.close()
    headers, _ = login(client, "extraSales0@x.test", "Northwind Logistics")
    assert client.delete("/diagnostic/me", headers=headers).json() == {"deleted": 1}

    assert dict(_dashboard(client)["top_risks"])["policy_unaware"] == 4
    report = client.get("/reports/me", headers=headers).json()
    assert report["answered"] == 0 and report["risks"] == [] and report["remediation"] == []
