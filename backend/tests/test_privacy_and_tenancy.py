from tests.conftest import add_respondents, login


def dash(client, headers, org_id=1):
    return client.get(f"/dashboard?org_id={org_id}", headers=headers)


def by_name(r):
    return {d["department"]: d for d in r.json()["departments"]}


# ---- Small groups (client request #1) ----

def test_small_departments_are_never_shown_alone(client):
    admin, _ = login(client, "asha@northwind.test", "Northwind Logistics")
    depts = by_name(dash(client, admin))
    assert set(depts) == {"Other teams"}                     # seed: no dept has 5 respondents
    other = depts["Other teams"]
    assert other["suppressed"] is True
    assert other["average_score"] is None and other["responded"] is None


def test_group_of_five_is_shown(client):
    add_respondents("Support", 4)                            # Priya + 4 = 5
    admin, _ = login(client, "asha@northwind.test", "Northwind Logistics")
    support = by_name(dash(client, admin))["Support"]
    assert support["suppressed"] is False
    assert support["responded"] == 5


def test_group_of_four_is_not_shown(client):
    add_respondents("Support", 3)                            # Priya + 3 = 4
    admin, _ = login(client, "asha@northwind.test", "Northwind Logistics")
    assert "Support" not in by_name(dash(client, admin))


def test_other_teams_shown_once_combined_group_is_large_enough(client):
    add_respondents("Support", 2)       # Support = 3 respondents
    add_respondents("Engineering", 2)   # Engineering = 2; with Support (3) and Sales (1) = 6
    admin, _ = login(client, "asha@northwind.test", "Northwind Logistics")
    other = by_name(dash(client, admin))["Other teams"]
    assert other["suppressed"] is False
    assert other["responded"] == 6


def test_top_risks_hidden_when_too_few_people_answered(client):
    admin, _ = login(client, "asha@northwind.test", "Northwind Logistics")
    assert dash(client, admin).json()["top_risks"] == []     # only 2 respondents in seed


def test_department_average_ignores_people_who_did_not_answer(client):
    add_respondents("Sales", 4, score=4)
    add_respondents("Engineering", 5, score=2)
    admin, _ = login(client, "asha@northwind.test", "Northwind Logistics")
    depts = by_name(dash(client, admin))
    assert depts["Sales"]["average_score"] == 4.0            # non-responders do not drag it down
    assert depts["Engineering"]["average_score"] == 2.0


# ---- Organization authorization ----

def test_select_org_allows_member(client):
    r = client.post("/auth/login", json={"email": "ravi@consult.test", "password": "pulse123"}).json()
    for org in r["organizations"]:
        resp = client.post("/auth/select-org", json={"org_id": org["org_id"]},
                           headers={"Authorization": f"Bearer {r['token']}"})
        assert resp.status_code == 200 and resp.json()["org_id"] == org["org_id"]


def test_select_org_rejects_org_user_is_not_in(client):
    r = client.post("/auth/login", json={"email": "priya@northwind.test", "password": "pulse123"}).json()
    h = {"Authorization": f"Bearer {r['token']}"}
    assert client.post("/auth/select-org", json={"org_id": 2}, headers=h).status_code == 403
    assert client.post("/auth/select-org", json={"org_id": 999}, headers=h).status_code == 403


def test_select_org_requires_login(client):
    assert client.post("/auth/select-org", json={"org_id": 1}).status_code == 401


def test_admin_cannot_read_another_orgs_dashboard(client):
    headers, _ = login(client, "ravi@consult.test", "Bluepeak Retail")   # admin of org 2 only
    assert dash(client, headers, org_id=1).status_code == 403
    assert dash(client, headers, org_id=2).status_code == 200


def test_employee_cannot_read_dashboard(client):
    headers, _ = login(client, "ravi@consult.test", "Northwind Logistics")   # employee at Northwind
    assert dash(client, headers, org_id=1).status_code == 403


# ---- Resubmitting ----

def test_resubmitting_replaces_instead_of_duplicating(client):
    headers, _ = login(client, "priya@northwind.test", "Northwind Logistics")
    body = {"answers": [{"question_id": "common-freq", "answer": "Daily"}]}
    client.post("/diagnostic/submit", headers=headers, json=body)
    client.post("/diagnostic/submit", headers=headers, json=body)
    assert client.get("/reports/me", headers=headers).json()["answered"] == 2   # seeded open answer + one freq
