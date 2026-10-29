from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.config import SECRET_KEY
from tests.conftest import login


def test_employee_cannot_read_admin_dashboard(client):
    headers, _ = login(client, "priya@northwind.test", "Northwind Logistics")
    assert client.get("/dashboard", headers=headers).status_code == 403


def test_multi_org_admin_cannot_use_other_memberships_permissions(client):
    headers, _ = login(client, "ravi@consult.test", "Northwind Logistics")
    assert client.get("/dashboard?org_id=2", headers=headers).status_code == 403
    headers, _ = login(client, "ravi@consult.test", "Bluepeak Retail")
    response = client.get("/dashboard?org_id=1", headers=headers)
    assert response.status_code == 200
    assert response.json()["organization"] == "Bluepeak Retail"


@pytest.mark.parametrize("kind", ["expired", "forged", "missing_exp", "invalid_sub", "invalid_org", "unknown_user", "nonmember"])
def test_rejects_invalid_tokens(client, kind):
    payload = {"sub": "1", "org": 1, "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
    key = SECRET_KEY
    expected = 401
    if kind == "expired":
        payload["exp"] = datetime.now(timezone.utc) - timedelta(seconds=1)
    elif kind == "forged":
        key = "a-different-secret-that-is-long-enough"
    elif kind == "missing_exp":
        del payload["exp"]
    elif kind == "invalid_sub":
        payload["sub"] = "not-an-integer"
    elif kind == "invalid_org":
        payload["org"] = True
    elif kind == "unknown_user":
        payload["sub"] = "9999"
        expected = 403
    else:
        payload["org"] = 2
        expected = 403
    token = jwt.encode(payload, key, algorithm="HS256")
    assert client.get("/dashboard", headers={"Authorization": f"Bearer {token}"}).status_code == expected


def test_missing_and_malformed_authorization_are_unauthorized(client):
    for authorization in [None, "Basic abc", "Bearer broken"]:
        headers = {"Authorization": authorization} if authorization else {}
        assert client.get("/dashboard", headers=headers).status_code == 401
