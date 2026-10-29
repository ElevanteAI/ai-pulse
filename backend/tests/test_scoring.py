import json
import os

import pytest

from app.services import llm, scoring
from tests.conftest import login


def fake_llm(monkeypatch, raw):
    monkeypatch.setattr(llm, "score_answer", lambda q, a: raw)


def test_valid_response(monkeypatch):
    fake_llm(monkeypatch, '{"score": 4, "reason": "Good.", "flags": ["unreviewed_output"]}')
    assert scoring.score_open_answer("q", "a") == {"score": 4, "reason": "Good.", "flags": ["unreviewed_output"]}


def test_markdown_fenced_json_is_accepted(monkeypatch):
    fake_llm(monkeypatch, '```json\n{"score": 4, "reason": "Fine.", "flags": []}\n```')
    assert scoring.score_open_answer("q", "a")["score"] == 4


@pytest.mark.parametrize("raw", [
    '{"score": 7, "reason": "Too high.", "flags": []}',
    '{"score": 0, "reason": "Too low.", "flags": []}',
    '{"score": "four", "reason": "Wrong type.", "flags": []}',
    '{"score": 3.5, "reason": "Not an int.", "flags": []}',
    '{"score": true, "reason": "Bool.", "flags": []}',
    '{"score": 3, "flags": []}',
    '{"reason": "No score.", "flags": []}',
    'I think this is a 4!',
    '[1, 2, 3]',
    '',
])
def test_invalid_responses_are_not_stored_as_scores(monkeypatch, raw):
    fake_llm(monkeypatch, raw)
    result = scoring.score_open_answer("q", "a")
    assert result["score"] is None and result["flags"] == []


def test_unknown_flags_are_dropped(monkeypatch):
    fake_llm(monkeypatch, '{"score": 2, "reason": "Limited.", "flags": ["probably_lying", "customer_data_shared"]}')
    assert scoring.score_open_answer("q", "a")["flags"] == ["customer_data_shared"]


def test_llm_outage_does_not_raise(monkeypatch):
    def boom(q, a):
        raise RuntimeError("LLM down")
    monkeypatch.setattr(llm, "score_answer", boom)
    assert scoring.score_open_answer("q", "a")["score"] is None


def test_every_canned_mock_response_is_handled(monkeypatch):
    path = os.path.join(os.path.dirname(__file__), "..", "data", "mock_ai_responses.json")
    for raw in json.load(open(path)):
        fake_llm(monkeypatch, raw)
        r = scoring.score_open_answer("q", "a")
        assert r["score"] is None or 1 <= r["score"] <= 5
        assert set(r["flags"]) <= scoring.ALLOWED_FLAGS


def test_submit_survives_bad_model_output(client, monkeypatch):
    monkeypatch.setattr(llm, "score_answer", lambda q, a: "not json at all")
    headers, _ = login(client, "priya@northwind.test", "Northwind Logistics")
    r = client.post("/diagnostic/submit", headers=headers,
                    json={"answers": [{"question_id": "common-open", "answer": "I use AI daily."}]})
    assert r.status_code == 200
