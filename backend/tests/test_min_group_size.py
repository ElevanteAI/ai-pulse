"""Client request #1: no group under 5 respondents is ever identifiable on the dashboard.

Seed: Northwind Sales 5 respondents, Support 6, Engineering 3, HR 2 (Imran, Ravi).
Bluepeak: Tom (Stores) and Kabir (Customer Care) only.
"""
import os
import subprocess
import sys

from app import models
from app.db import SessionLocal
from tests.conftest import login


def dashboard(client, email="asha@northwind.test", org="Northwind Logistics"):
    headers, _ = login(client, email, org)
    return client.get("/dashboard", headers=headers).json()


def names(data):
    return [g["department"] for g in data["groups"]]


def clear_answers(email, org_name):
    db = SessionLocal()
    m = (db.query(models.Membership).join(models.User).join(models.Organization)
         .filter(models.User.email == email, models.Organization.name == org_name).one())
    db.query(models.Response).filter_by(membership_id=m.id).delete()
    db.commit()


def assert_no_small_group_visible(data):
    for g in data["groups"]:
        assert g["respondents"] >= data["min_group_size"], g
    # Subtraction attack: overall must be built from exactly the shown groups, nothing else
    if data["overall"]:
        assert data["overall"]["respondents"] == sum(g["respondents"] for g in data["groups"])


def test_large_departments_shown_small_ones_pooled(client):
    data = dashboard(client)
    assert names(data) == ["Sales", "Support", "Other teams"]
    other = data["groups"][-1]
    assert other["respondents"] == 5
    assert other["includes"] == ["Engineering", "HR", "No department"]  # Asha (admin) has no department
    assert data["not_shown"] == [{"department": "Engineering"}, {"department": "HR"}]
    assert data["small_teams_left_out"] is False
    assert_no_small_group_visible(data)


def test_pool_still_too_small_is_hidden_everywhere(client):
    clear_answers("omar@northwind.test", "Northwind Logistics")  # Other teams drops to 4
    data = dashboard(client)
    assert names(data) == ["Sales", "Support"]
    assert data["small_teams_left_out"] is True
    assert data["not_shown"] == [{"department": "Engineering"}, {"department": "HR"}]
    assert data["overall"]["respondents"] == 11  # Sales 5 + Support 6, not 15
    assert_no_small_group_visible(data)


def test_hidden_people_do_not_leak_through_risks(client):
    """Omar (Engineering) has unreviewed_output. Once the Engineering+HR pool drops below 5 and is
    hidden, his flag must not be counted in the org-wide risks either."""
    clear_answers("ravi@consult.test", "Northwind Logistics")  # pool: Eng 3 + Imran = 4 -> hidden
    data = dashboard(client)
    shown_people = sum(g["respondents"] for g in data["groups"])
    for r in data["top_risks"]:
        assert r["people"] <= shown_people
    # unreviewed_output: Rohan + Meghna are in shown groups (2); Omar is hidden
    risks = {r["risk"]: r["people"] for r in data["top_risks"]}
    assert risks["unreviewed_output"] == 2


def test_teams_not_shown_reveal_nothing_about_who_took_part(client):
    """Kabir is the only person in Bluepeak's Customer Care. The page must look the same whether or
    not he has answered, or leadership learns that he took part, and later that he deleted."""
    before = dashboard(client, "meera@bluepeak.test", "Bluepeak Retail")
    h, _ = login(client, "kabir@bluepeak.test", "Bluepeak Retail")
    client.delete("/reports/me", headers=h)
    after = dashboard(client, "meera@bluepeak.test", "Bluepeak Retail")
    assert before == after
    assert all(set(n) == {"department"} for n in after["not_shown"])  # no status, no headcount


def test_tiny_org_shows_no_scores_at_all(client):
    data = dashboard(client, "meera@bluepeak.test", "Bluepeak Retail")
    assert data["groups"] == []
    assert data["overall"] is None
    assert data["top_risks"] == []  # Kabir's confidential_data_shared must not appear
    assert data["ai_scoring"] is None
    assert data["small_teams_left_out"] is True
    assert "customer" not in str(data) and "confidential" not in str(data)


def test_department_reaching_threshold_appears_on_its_own(client):
    db = SessionLocal()
    nw = db.query(models.Organization).filter_by(name="Northwind Logistics").one()
    eng = next(d for d in nw.departments if d.name == "Engineering")
    for i in range(2):
        u = models.User(name=f"New {i}", email=f"new{i}@northwind.test", password_hash="x")
        db.add(u)
        db.flush()
        m = models.Membership(user_id=u.id, org_id=nw.id, department_id=eng.id, role="employee",
                              job_role="engineering", seniority="mid")
        db.add(m)
        db.flush()
        db.add(models.Response(membership_id=m.id, question_id="common-freq", answer="Daily", score=4))
    db.commit()
    data = dashboard(client)
    assert "Engineering" in names(data)  # 5 respondents now
    assert "Other teams" not in names(data)  # HR alone (2) can't be pooled into anything big enough
    assert data["small_teams_left_out"] is True
    assert_no_small_group_visible(data)


def test_threshold_cannot_be_configured_below_five():
    env = {**os.environ, "MIN_GROUP_SIZE": "2", "APP_ENV": "test"}
    out = subprocess.run([sys.executable, "-c", "from app.config import MIN_GROUP_SIZE; print(MIN_GROUP_SIZE)"],
                         env=env, capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__)))
    assert out.stdout.strip() == "5"
