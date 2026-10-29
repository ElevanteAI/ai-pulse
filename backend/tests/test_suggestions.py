import json
from types import SimpleNamespace

import httpx
import pytest

from app.services import llm
from app.services.suggestions import suggestion_data, validate_suggestions
from tests.conftest import login


GOOD = [{"title": "Review a draft", "action": "Check a draft against a trusted source."}] * 3


@pytest.mark.parametrize("value", ["bad", "{}", "[]", "null", json.dumps([{}] * 3), json.dumps([{"title": "Unsafe", "action": "Upload confidential data to a chatbot."}] * 3), json.dumps([{"title": "Link", "action": "Visit https://evil.test."}] * 3), json.dumps([{"title": "Markup", "action": "<script>alert(1)</script>"}] * 3)])
def test_rejects_malformed_or_unsafe_suggestions(value):
    with pytest.raises(ValueError):
        validate_suggestions(value)


def test_repairs_fences_and_caps_lengths():
    items = [{"title": "x" * 100, "action": "a" * 300}] * 3
    result = validate_suggestions("```json\n" + json.dumps(items) + "\n```")
    assert len(result) == 3
    assert len(result[0]["title"]) == 60
    assert len(result[0]["action"]) <= 240


def test_payload_excludes_open_text_and_identifying_fields():
    rows = [SimpleNamespace(question_id="common-open", answer="Alice alice@example.com Northwind Logistics", score=2, flags=["policy_unaware"], reason="Alice"), SimpleNamespace(question_id="common-freq", answer="Daily", score=4, flags=[])]
    data = suggestion_data("sales", "junior", rows)
    encoded = json.dumps(data)
    for private in ["Alice", "alice@example.com", "Northwind", "reason", "membership_id"]:
        assert private not in encoded
    assert data["responses"][1]["selected_option"] == "Daily"


def test_endpoint_uses_only_callers_data_and_clears_after_delete(client, monkeypatch):
    captured = []
    def suggest(data):
        captured.append(data)
        return json.dumps(GOOD)
    monkeypatch.setattr(llm, "suggest_improvements", suggest)
    headers, _ = login(client, "neha@northwind.test", "Northwind Logistics")
    response = client.post("/reports/me/suggestions", headers=headers)
    assert response.status_code == 200
    assert response.json()["source"] == "ai"
    assert len(captured[0]["responses"]) == 6
    assert captured[0]["role"] == "sales"
    assert captured[0]["seniority"] == "junior"
    client.delete("/reports/me", headers=headers)
    assert client.post("/reports/me/suggestions", headers=headers).json() == {"suggestions": [], "source": "none"}
    assert len(captured) == 1


@pytest.mark.parametrize("failure", ["malformed", httpx.ReadTimeout("timeout")])
def test_endpoint_falls_back_after_two_failures(client, monkeypatch, failure):
    calls = []
    def suggest(data):
        calls.append(data)
        if isinstance(failure, Exception):
            raise failure
        return failure
    monkeypatch.setattr(llm, "suggest_improvements", suggest)
    headers, _ = login(client, "neha@northwind.test", "Northwind Logistics")
    data = client.post("/reports/me/suggestions", headers=headers).json()
    assert data["source"] == "static"
    assert len(data["suggestions"]) == 3
    assert len(calls) == 2


@pytest.mark.parametrize("role", ["sales", "support", "engineering", "manager"])
def test_mock_suggestions_validate(role):
    raw = llm.suggest_improvements({"role": role, "responses": []})
    assert len(validate_suggestions(raw)) == 3


def test_suggestions_require_authentication(client):
    assert client.post("/reports/me/suggestions").status_code == 401
