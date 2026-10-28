from app.services.questions import questions_for


def ids(qs):
    return {q["id"] for q in qs}


def test_everyone_gets_common_questions():
    got = ids(questions_for("sales", "junior"))
    assert {"common-freq", "common-policy", "common-data", "common-review", "common-open"} <= got


def test_junior_engineer_does_not_get_senior_questions():
    got = ids(questions_for("engineering", "junior"))
    assert "eng-assistant" in got
    assert "eng-review" not in got
    assert "eng-arch" not in got


def test_senior_support_gets_escalation_question():
    assert "sup-escalation" in ids(questions_for("support", "senior"))


def test_lead_manager_gets_policy_questions():
    got = ids(questions_for("manager", "lead"))
    assert "mgr-policy" in got
    assert "mgr-open" in got


def test_lead_engineer_gets_every_engineering_question():
    """Seniority used to be compared as strings, and "lead" < "mid" alphabetically."""
    assert {"eng-assistant", "eng-review", "eng-arch"} <= ids(questions_for("engineering", "lead"))


def test_seniority_is_monotonic():
    """Someone more senior never gets fewer questions than someone less senior."""
    levels = ["junior", "mid", "senior", "lead"]
    for role in ("support", "engineering", "sales", "manager"):
        sets = [ids(questions_for(role, s)) for s in levels]
        for lower, higher in zip(sets, sets[1:]):
            assert lower <= higher, role


def test_unknown_seniority_is_rejected():
    import pytest
    with pytest.raises(ValueError):
        questions_for("sales", "intern")
