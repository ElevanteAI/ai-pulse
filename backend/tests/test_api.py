from tests.conftest import login


def test_login_lists_organizations(client):
    _, data = login(client, "ravi@consult.test")
    names = {o["org_name"] for o in data["organizations"]}
    assert names == {"Northwind Logistics", "Bluepeak Retail"}


def test_cannot_select_org_without_membership(client):
    headers, _ = login(client, "asha@northwind.test", "Northwind Logistics")
    r = client.post("/auth/select-org", json={"org_id": 2}, headers=headers)
    assert r.status_code == 403


def test_can_select_own_org(client):
    headers, data = login(client, "ravi@consult.test")
    org_id = data["organizations"][0]["org_id"]
    r = client.post("/auth/select-org", json={"org_id": org_id}, headers=headers)
    assert r.status_code == 200
    assert r.json()["org_id"] == org_id


def test_employee_sees_questions(client):
    headers, _ = login(client, "priya@northwind.test", "Northwind Logistics")
    r = client.get("/diagnostic/questions", headers=headers)
    assert r.status_code == 200
    assert any(q["id"] == "sup-drafts" for q in r.json())


def test_admin_dashboard(client):
    headers, data = login(client, "asha@northwind.test", "Northwind Logistics")
    org_id = data["organizations"][0]["org_id"]
    r = client.get(f"/dashboard?org_id={org_id}", headers=headers)
    assert r.status_code == 200
    # Every Northwind department has fewer than 5 respondents, so only the pooled row appears
    rows = r.json()["departments"]
    assert [d["department"] for d in rows] == ["Other teams"]
    assert rows[0]["average_score"] is None and rows[0]["suppressed"] is True
    assert r.json()["top_risks"] == []
    totals = r.json()["totals"]
    assert totals["headcount"] == 10 and totals["completed"] == 2  # seed: 9 + consultant, 2 responders
    assert totals["average_score"] is None and totals["level"] == "Not assessed"


def test_admin_cannot_see_other_org(client):
    headers, _ = login(client, "asha@northwind.test", "Northwind Logistics")
    # Asha is admin of Northwind (org 1); org 2 is Bluepeak
    r = client.get("/dashboard?org_id=2", headers=headers)
    assert r.status_code == 403


def test_resubmitting_replaces_previous_answers(client):
    headers, _ = login(client, "priya@northwind.test", "Northwind Logistics")
    option = client.get("/diagnostic/questions", headers=headers).json()[0]["options"][0]
    body = {"answers": [{"question_id": "common-freq", "answer": option}]}
    admin, data = login(client, "asha@northwind.test", "Northwind Logistics")
    dash = f"/dashboard?org_id={data['organizations'][0]['org_id']}"

    client.post("/diagnostic/submit", json=body, headers=headers)
    once = client.get(dash, headers=admin).json()
    client.post("/diagnostic/submit", json=body, headers=headers)
    twice = client.get(dash, headers=admin).json()
    assert once == twice

    # The dashboard hides duplicates (it averages per employee), so also count the stored rows.
    # Priya had 2 seeded answers; the submit replaces them with exactly one.
    from app.db import SessionLocal
    from app import models
    db = SessionLocal()
    user = db.query(models.User).filter_by(email="priya@northwind.test").one()
    rows = db.query(models.Response).join(models.Membership).filter(models.Membership.user_id == user.id).count()
    db.close()
    assert rows == 1


def _add_respondents(org_name, dept_name, count, flag=None):
    """Give a department `count` extra employees who each answered once."""
    from app.db import SessionLocal
    from app import models
    db = SessionLocal()
    org = db.query(models.Organization).filter_by(name=org_name).one()
    dept = db.query(models.Department).filter_by(org_id=org.id, name=dept_name).one()
    for i in range(count):
        u = models.User(name=f"Extra {dept_name} {i}", email=f"extra{dept_name}{i}@x.test", password_hash="x")
        db.add(u)
        db.flush()
        m = models.Membership(user_id=u.id, org_id=org.id, department_id=dept.id,
                              role="employee", job_role="sales", seniority="mid")
        db.add(m)
        db.flush()
        db.add(models.Response(membership_id=m.id, question_id="common-freq", answer="x", score=4,
                               flags=[flag] if flag else []))
    db.commit()
    db.close()


def _dashboard(client):
    headers, data = login(client, "asha@northwind.test", "Northwind Logistics")
    return client.get(f"/dashboard?org_id={data['organizations'][0]['org_id']}", headers=headers).json()


def test_large_department_visible_small_ones_pooled(client):
    _add_respondents("Northwind Logistics", "Sales", 5, flag="policy_unaware")
    d = _dashboard(client)
    by_name = {row["department"]: row for row in d["departments"]}
    assert set(by_name) == {"Sales", "Other teams"}
    assert by_name["Sales"]["average_score"] is not None and by_name["Sales"]["suppressed"] is False
    assert by_name["Other teams"]["suppressed"] is True
    assert by_name["Other teams"]["average_score"] is None
    # Priya's customer_data_shared flag comes from a small group and must not leak
    assert dict(d["top_risks"]) == {"policy_unaware": 5}


def test_pooled_other_teams_shown_once_it_reaches_five(client):
    _add_respondents("Northwind Logistics", "HR", 4)  # HR (4+0) plus Support (1 seeded) = 5 pooled
    d = _dashboard(client)
    pooled = next(row for row in d["departments"] if row["department"] == "Other teams")
    assert pooled["suppressed"] is False and pooled["responded"] >= 5


def test_employee_can_delete_own_responses(client):
    headers, _ = login(client, "priya@northwind.test", "Northwind Logistics")
    assert client.get("/reports/me", headers=headers).json()["answered"] == 2

    r = client.delete("/diagnostic/me", headers=headers)
    assert r.status_code == 200 and r.json() == {"deleted": 2}

    report = client.get("/reports/me", headers=headers).json()
    assert report["answered"] == 0
    assert report["average_score"] is None and report["risks"] == []


def test_delete_requires_login(client):
    assert client.delete("/diagnostic/me").status_code in (401, 403)


def test_delete_recalculates_dashboard(client):
    _add_respondents("Northwind Logistics", "Sales", 5)
    before = next(r for r in _dashboard(client)["departments"] if r["department"] == "Sales")
    assert before["responded"] == 6  # 5 extras + Vikram
    headers, _ = login(client, "vikram@northwind.test", "Northwind Logistics")
    client.delete("/diagnostic/me", headers=headers)
    after = next(r for r in _dashboard(client)["departments"] if r["department"] == "Sales")
    assert after["responded"] == 5
    assert after["average_score"] == 4.0  # Vikram's 4s are gone, only the extras' 4s remain


def test_deleting_can_drop_a_department_below_threshold(client):
    _add_respondents("Northwind Logistics", "Sales", 4)  # 4 extras + Vikram = 5, visible
    assert "Sales" in {r["department"] for r in _dashboard(client)["departments"]}
    headers, _ = login(client, "vikram@northwind.test", "Northwind Logistics")
    client.delete("/diagnostic/me", headers=headers)
    assert "Sales" not in {r["department"] for r in _dashboard(client)["departments"]}


def test_report_includes_remediation_for_flagged_risks(client):
    headers, _ = login(client, "priya@northwind.test", "Northwind Logistics")
    rem = client.get("/reports/me", headers=headers).json()["remediation"]
    assert [r["risk"] for r in rem] == ["customer_data_shared"]
    assert rem[0]["tips"]


def test_report_has_no_remediation_without_risks(client):
    headers, _ = login(client, "vikram@northwind.test", "Northwind Logistics")
    assert client.get("/reports/me", headers=headers).json()["remediation"] == []


def test_admin_gets_executive_playbook(client):
    headers, _ = login(client, "asha@northwind.test", "Northwind Logistics")
    r = client.get("/playbooks/customer_data_shared", headers=headers)
    assert r.status_code == 200
    card = r.json()
    assert card["guardrails"] and card["approved_tooling"] and card["team_guidance"]


def test_playbook_unknown_risk_404(client):
    headers, _ = login(client, "asha@northwind.test", "Northwind Logistics")
    assert client.get("/playbooks/nope", headers=headers).status_code == 404


def test_employee_cannot_read_executive_playbook(client):
    headers, _ = login(client, "priya@northwind.test", "Northwind Logistics")
    assert client.get("/playbooks/customer_data_shared", headers=headers).status_code == 403
