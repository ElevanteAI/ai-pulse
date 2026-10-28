import pytest

from app.services import scoring


def test_scoring_rejects_invalid_model_score(monkeypatch):
    monkeypatch.setattr(scoring.llm, "score_answer", lambda *_: '{"score": 7, "reason": "x", "flags": []}')
    with pytest.raises(scoring.ScoringError):
        scoring.score_open_answer("question", "answer")


def test_scoring_accepts_json_inside_markdown_fence(monkeypatch):
    monkeypatch.setattr(scoring.llm, "score_answer", lambda *_: '```json\n{"score": 4, "reason": "Reviewed output", "flags": []}\n```')
    assert scoring.score_open_answer("question", "answer")["score"] == 4
