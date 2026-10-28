from app.services.recommendations import get_recommendations, load_resources


class DummyResponse:
    def __init__(self, question_id: str, score: int, flags: list[str] = None):
        self.question_id = question_id
        self.score = score
        self.flags = flags or []


def test_resources_load_and_have_required_fields():
    resources = load_resources()
    assert len(resources) >= 5
    for r in resources:
        assert r["id"]
        assert r["title"]
        url = r.get("bonus_url") or r.get("url")
        assert url and url.startswith("https://")
        assert r["practice"]
        assert r["success_measure"]
        assert r["duration_minutes"] > 0
        assert isinstance(r["roles"], list)


def test_data_safety_risk_flag_prioritization():
    responses = [
        DummyResponse("common-freq", 4),
        DummyResponse("common-open", 2, flags=["customer_data_shared"]),
    ]
    recs = get_recommendations(
        job_role="support",
        seniority="mid",
        responses=responses,
        risk_flags=["customer_data_shared"],
    )
    assert len(recs) > 0
    # First recommendation must be data safety
    first = recs[0]
    assert first["topic"] == "data_safety"
    assert "data privacy or confidentiality risk" in first["why"]


def test_engineering_output_verification_recommendation():
    responses = [
        DummyResponse("common-freq", 4),
        DummyResponse("eng-review", 2),
    ]
    recs = get_recommendations(
        job_role="engineering",
        seniority="senior",
        responses=responses,
        risk_flags=[],
    )
    topics = [r["topic"] for r in recs]
    assert "output_verification" in topics
    assert any("eng" in r["id"] or "code" in r["id"] for r in recs)


def test_support_role_excludes_developer_coding_packs():
    responses = [
        DummyResponse("common-freq", 3),
        DummyResponse("sup-drafts", 3),
    ]
    recs = get_recommendations(
        job_role="support",
        seniority="junior",
        responses=responses,
        risk_flags=[],
    )
    # Support employees must not receive engineering-specific coding refactor packs
    assert all("engineering" not in r["id"] or "prompt" in r["id"] or "data" in r["id"] for r in recs)


def test_empty_responses_return_empty_recommendations():
    assert get_recommendations("engineering", "lead", [], []) == []


def test_in_platform_practice_evaluation():
    from app.services.recommendations import evaluate_practice_attempt
    result = evaluate_practice_attempt(
        practice_id="owasp-llm-data-protection",
        scenario_description="Strip PII from incoming customer query",
        user_solution="Dear [CUSTOMER_NAME], your order [ORDER_ID] has been checked.",
    )
    assert result["passed"] is True
    assert "feedback" in result
    assert result["score"] >= 3

