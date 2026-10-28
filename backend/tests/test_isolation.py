"""Tenant isolation: data must never cross organizations or roles.

These replace the original test_admin_cannot_see_other_org, which asserted a 200
and used the admin's own org id, so it could never catch the leak.
"""
from tests.conftest import login


def test_admin_only_sees_own_org_even_if_asking_for_another(client):
    headers, _ = login(client, "asha@northwind.test", "Northwind Logistics")
    # The old API took ?org_id=. Passing Bluepeak's id must have no effect.
    for org_id in (1, 2, 999):
        r = client.get(f"/dashboard?org_id={org_id}", headers=headers)
        assert r.status_code == 200
        assert r.json()["organization"] == "Northwind Logistics"


def test_bluepeak_admin_never_sees_northwind(client):
    headers, _ = login(client, "meera@bluepeak.test", "Bluepeak Retail")
    r = client.get("/dashboard?org_id=1", headers=headers)
    assert r.json()["organization"] == "Bluepeak Retail"
    assert "Sales" not in str(r.json())  # Northwind department names


def test_consultant_admin_in_one_org_is_employee_in_the_other(client):
    """Ravi is admin at Bluepeak but only an employee at Northwind."""
    headers, _ = login(client, "ravi@consult.test", "Bluepeak Retail")
    r = client.get("/dashboard?org_id=1", headers=headers)
    assert r.json()["organization"] == "Bluepeak Retail"

    headers, _ = login(client, "ravi@consult.test", "Northwind Logistics")
    assert client.get("/dashboard", headers=headers).status_code == 403


def test_employee_cannot_see_dashboard(client):
    headers, _ = login(client, "priya@northwind.test", "Northwind Logistics")
    assert client.get("/dashboard", headers=headers).status_code == 403


def test_token_without_org_cannot_reach_org_data(client):
    headers, _ = login(client, "asha@northwind.test")  # logged in, no org selected yet
    assert client.get("/dashboard", headers=headers).status_code == 400
    assert client.get("/reports/me", headers=headers).status_code == 400


def test_report_is_per_org_for_multi_org_user(client):
    nw, _ = login(client, "ravi@consult.test", "Northwind Logistics")
    bp, _ = login(client, "ravi@consult.test", "Bluepeak Retail")
    assert client.get("/reports/me", headers=nw).json()["organization"] == "Northwind Logistics"
    assert client.get("/reports/me", headers=bp).json()["organization"] == "Bluepeak Retail"
