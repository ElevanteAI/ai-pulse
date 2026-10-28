from tests.conftest import login


def test_user_cannot_select_an_organization_they_do_not_belong_to(client):
    headers, _ = login(client, "priya@northwind.test")
    response = client.post("/auth/select-org", json={"org_id": 2}, headers=headers)
    assert response.status_code == 403
