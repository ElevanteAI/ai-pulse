"""The evaluation harness itself must be right, or its numbers mean nothing."""
import json

from app import eval as ev
from app.services import llm, scoring
from app.services.questions import load_questions


def test_eval_set_is_well_formed():
    data = ev.load_cases()
    cases = data["cases"]
    question_ids = {q["id"] for q in load_questions()}
    assert len(cases) >= 25
    assert len({c["id"] for c in cases}) == len(cases)
    for c in cases:
        lo, hi = c["expected_score"]
        assert 1 <= lo <= hi <= 5, c["id"]
        assert set(c["expected_flags"]) <= scoring.ALLOWED_FLAGS, c["id"]
        assert c["question"] in question_ids, c["id"]
    assert sum(c["injection"] for c in cases) >= 5
    for flag in scoring.ALLOWED_FLAGS:  # every flag has at least one positive example
        assert any(flag in c["expected_flags"] and not c["injection"] for c in cases), flag


def _rec(id, lo, hi, score, flags, expected_flags=(), injection=False, screened=False):
    return {"id": id, "expected_score": [lo, hi], "score": score, "flags": list(flags),
            "expected_flags": list(expected_flags), "injection": injection, "screened": screened,
            "status": scoring.SCORED if score is not None else scoring.NEEDS_REVIEW}


def test_metrics_match_hand_calculation():
    records = [
        _rec("a", 3, 4, 4, ["unreviewed_output"], ["unreviewed_output"]),  # in range, flag tp
        _rec("b", 2, 2, 4, ["customer_data_shared"]),                      # over by 2, flag fp
        _rec("c", 4, 5, 3, [], ["policy_unaware"]),                         # under by 1, flag fn
        _rec("d", 5, 5, None, [], screened=True),                           # legit, wrongly screened
        _rec("e", 1, 1, 5, [], injection=True),                             # injection accepted, inflated
        _rec("f", 3, 3, None, [], ["customer_data_shared"], injection=True, screened=True),
    ]
    m = ev.metrics(records)
    assert m["legit"]["total"] == 4 and m["legit"]["scored"] == 3 and m["legit"]["in_range"] == 1
    assert m["legit"]["over_scored"] == ["b"] and m["legit"]["under_scored"] == ["c"]
    assert m["legit"]["mean_distance_from_range"] == (0 + 2 + 1) / 3
    assert m["legit"]["screened_by_mistake"] == ["d"]
    overall = m["flags"]["overall"]
    assert (overall["tp"], overall["fp"], overall["fn"]) == (1, 1, 1)
    assert overall["precision"] == 0.5 and overall["recall"] == 0.5
    assert m["injection"]["screened"] == ["f"]
    assert m["injection"]["accepted_above_honest_range"] == ["e"]
    assert m["model_replies_failing_validation"] == []


def test_a_model_that_agrees_with_the_labels_scores_perfectly(monkeypatch):
    """End to end through the real score_open_answer: a fake model that returns the label."""
    cases = {c["answer"]: c for c in ev.load_cases()["cases"]}

    def oracle(question, answer):
        c = cases[answer]
        return json.dumps({"score": c["expected_score"][0], "reason": "ok", "flags": c["expected_flags"]})
    monkeypatch.setattr(llm, "score_answer", oracle)

    m = ev.metrics(ev.run(list(cases.values())))
    assert m["legit"]["in_range"] == m["legit"]["scored"]
    assert m["legit"]["over_scored"] == m["legit"]["under_scored"] == []
    assert m["flags"]["overall"]["fp"] == m["flags"]["overall"]["fn"] == 0
    assert m["model_replies_failing_validation"] == []
