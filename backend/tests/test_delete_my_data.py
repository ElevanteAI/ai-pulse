from tests.conftest import add_respondents, login


def dept(client, headers, name):
    r = client.get("/dashboard?org_id=1", headers=headers)
    return next(d for d in r.json()["departments"] if d["department"] == name)


def names(client, headers):
    return [d["department"] for d in client.get("/dashboard?org_id=1", headers=headers).json()["departments"]]


def test_delete_removes_my_answers_and_report(client):
    headers, _ = login(client, "priya@northwind.test", "Northwind Logistics")
    assert client.get("/reports/me", headers=headers).json()["answered"] == 2   # seeded

    r = client.delete("/reports/me", headers=headers)
    assert r.status_code == 200
    assert r.json() == {"deleted": 2}

    report = client.get("/reports/me", headers=headers).json()
    assert report["answered"] == 0
    assert report["average_score"] is None
    assert report["level"] == "Not assessed"
    assert report["risks"] == []


def test_deleted_data_disappears_from_dashboard_immediately(client):
    add_respondents("Support", 4, flags=["policy_unaware"])   # Support: Priya + 4 = 5 respondents
    admin, _ = login(client, "asha@northwind.test", "Northwind Logistics")
    assert dept(client, admin, "Support")["responded"] == 5
    top = dict(client.get("/dashboard?org_id=1", headers=admin).json()["top_risks"])
    assert top["customer_data_shared"] == 1                  # Priya's risk

    priya, _ = login(client, "priya@northwind.test", "Northwind Logistics")
    client.delete("/reports/me", headers=priya)

    # 4 respondents left: Support folds into "Other teams" and Priya's risk is gone
    assert "Support" not in names(client, admin)
    top = dict(client.get("/dashboard?org_id=1", headers=admin).json()["top_risks"])
    assert "customer_data_shared" not in top


def test_delete_only_affects_the_caller(client):
    add_respondents("Sales", 4)                              # Sales: Vikram + 4 = 5 respondents
    admin, _ = login(client, "asha@northwind.test", "Northwind Logistics")
    priya, _ = login(client, "priya@northwind.test", "Northwind Logistics")
    client.delete("/reports/me", headers=priya)

    vikram, _ = login(client, "vikram@northwind.test", "Northwind Logistics")
    assert client.get("/reports/me", headers=vikram).json()["answered"] == 2
    assert dept(client, admin, "Sales")["responded"] == 5


def test_delete_is_idempotent(client):
    headers, _ = login(client, "priya@northwind.test", "Northwind Logistics")
    client.delete("/reports/me", headers=headers)
    r = client.delete("/reports/me", headers=headers)
    assert r.status_code == 200
    assert r.json() == {"deleted": 0}


def test_delete_requires_login(client):
    assert client.delete("/reports/me").status_code == 401


def test_delete_only_touches_selected_organization(client):
    # Ravi answers in Northwind and in Bluepeak; deleting in one org must keep the other
    nw, _ = login(client, "ravi@consult.test", "Northwind Logistics")
    bp, _ = login(client, "ravi@consult.test", "Bluepeak Retail")
    for headers in (nw, bp):
        client.post("/diagnostic/submit", headers=headers,
                    json={"answers": [{"question_id": "common-freq", "answer": "Daily"}]})

    client.delete("/reports/me", headers=nw)

    assert client.get("/reports/me", headers=nw).json()["answered"] == 0
    assert client.get("/reports/me", headers=bp).json()["answered"] == 1
