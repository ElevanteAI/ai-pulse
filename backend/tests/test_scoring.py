import pytest

from app.services import scoring


def run(monkeypatch, raw):
    def fake(question, answer):
        if isinstance(raw, Exception):
            raise raw
        return raw
    monkeypatch.setattr(scoring.llm, "score_answer", fake)
    return scoring.score_open_answer("q", "a")


def test_clean_json(monkeypatch):
    r = run(monkeypatch, '{"score": 4, "reason": "Good.", "flags": ["unreviewed_output"]}')
    assert r == {"score": 4.0, "reason": "Good.", "flags": ["unreviewed_output"]}


def test_markdown_fenced_json(monkeypatch):
    r = run(monkeypatch, 'Here you go:\n```json\n{"score": 2, "reason": "Basic.", "flags": []}\n```')
    assert r["score"] == 2.0 and r["reason"] == "Basic."


def test_json_surrounded_by_prose(monkeypatch):
    r = run(monkeypatch, 'Sure! {"score": 5, "reason": "Great.", "flags": []} Hope that helps.')
    assert r["score"] == 5.0


@pytest.mark.parametrize("given,expected", [(7, 5.0), (0, 1.0), (-3, 1.0), ("4", 4.0), ("four", 4.0), (3.5, 3.5)])
def test_score_is_coerced_and_clamped(monkeypatch, given, expected):
    import json
    r = run(monkeypatch, json.dumps({"score": given, "reason": "x", "flags": []}))
    assert r["score"] == expected


def test_hallucinated_flags_are_dropped(monkeypatch):
    r = run(monkeypatch, '{"score": 3, "reason": "x", "flags": ["policy_unaware", "made_up", 5, "policy_unaware"]}')
    assert r["flags"] == ["policy_unaware"]


def test_missing_reason_and_flags_get_defaults(monkeypatch):
    r = run(monkeypatch, '{"score": 3}')
    assert r["reason"] == scoring.DEFAULT_REASON
    assert r["flags"] == []


@pytest.mark.parametrize("raw", [
    "totally not json",
    "[1, 2, 3]",
    '{"score": "great", "reason": "x"}',
    '{"reason": "no score"}',
    TimeoutError("model timed out"),
])
def test_failures_fall_back_to_default(monkeypatch, raw):
    r = run(monkeypatch, raw)
    assert r == {"score": scoring.DEFAULT_SCORE, "reason": scoring.FALLBACK_REASON, "flags": []}
