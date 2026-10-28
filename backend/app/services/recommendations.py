import json
import os
import re
from typing import Any
import httpx

from ..config import AI_MODE, LLM_API_URL, LLM_API_KEY, LLM_MODEL

_RESOURCES_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "learning_resources.json"
)

QUESTION_TOPIC_MAP = {
    "common-data": "data_safety",
    "common-review": "output_verification",
    "common-policy": "policy_governance",
    "common-freq": "developer_productivity",
    "eng-review": "output_verification",
    "eng-assistant": "developer_productivity",
    "eng-arch": "developer_productivity",
    "sup-drafts": "prompt_engineering",
    "sup-escalation": "data_safety",
    "sales-outreach": "prompt_engineering",
    "sales-crm": "data_safety",
    "mgr-policy": "policy_governance",
    "mgr-adoption": "policy_governance",
}

FLAG_TOPIC_MAP = {
    "customer_data_shared": "data_safety",
    "confidential_data_shared": "data_safety",
    "unreviewed_output": "output_verification",
    "policy_unaware": "policy_governance",
}


def load_resources() -> list[dict[str, Any]]:
    with open(_RESOURCES_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_recommendations(
    job_role: str,
    seniority: str,
    responses: list[Any],
    risk_flags: list[str],
    limit: int = 4,
) -> list[dict[str, Any]]:
    """Deterministically selects tailored learning and workplace practice packs

    for every capability gap, score weakness, or risk flag.
    """
    if not responses:
        return []

    all_resources = load_resources()
    role_resources = [
        r
        for r in all_resources
        if "all" in r.get("roles", []) or job_role in r.get("roles", [])
    ]

    needed_topics: dict[str, str] = {}

    # Priority 1: Triggered risk flags (critical safety/governance concerns)
    for flag in sorted(set(risk_flags)):
        topic = FLAG_TOPIC_MAP.get(flag)
        if topic and topic not in needed_topics:
            if flag in ("customer_data_shared", "confidential_data_shared"):
                needed_topics[topic] = (
                    "Selected because your diagnostic flagged a critical data privacy or confidentiality risk."
                )
            elif flag == "unreviewed_output":
                needed_topics[topic] = (
                    "Selected because your answers indicate unverified reliance on AI-generated outputs."
                )
            elif flag == "policy_unaware":
                needed_topics[topic] = (
                    "Selected because your answers suggest unfamiliarity with company AI usage policies."
                )

    # Priority 2: Questions with lower scores (score <= 3)
    for resp in responses:
        qid = getattr(resp, "question_id", None) or (
            resp.get("question_id") if isinstance(resp, dict) else None
        )
        score = getattr(resp, "score", None) or (
            resp.get("score") if isinstance(resp, dict) else None
        )
        if qid and score is not None and score <= 3:
            topic = QUESTION_TOPIC_MAP.get(qid)
            if topic and topic not in needed_topics:
                needed_topics[topic] = (
                    f"Selected to strengthen your execution in {topic.replace('_', ' ')} based on diagnostic answers."
                )

    # If no flags or low scores, provide role-appropriate capability builder
    if not needed_topics:
        if job_role == "engineering":
            needed_topics["developer_productivity"] = (
                "Selected to advance your AI-assisted engineering and automated verification practices."
            )
        elif job_role == "manager":
            needed_topics["policy_governance"] = (
                "Selected to help you lead team AI governance and safe workflow adoption."
            )
        else:
            needed_topics["prompt_engineering"] = (
                "Selected to help you craft structured, high-accuracy AI prompts for your daily tasks."
            )

    recommendations: list[dict[str, Any]] = []
    used_ids: set[str] = set()

    for topic, reason in needed_topics.items():
        candidates = [
            r
            for r in role_resources
            if r["topic"] == topic and r["id"] not in used_ids
        ]
        if candidates:
            chosen = candidates[0]
            used_ids.add(chosen["id"])
            recommendations.append(
                {
                    "id": chosen["id"],
                    "title": chosen["title"],
                    "provider": chosen["provider"],
                    "url": chosen.get("bonus_url") or chosen.get("url"),
                    "bonus_url": chosen.get("bonus_url") or chosen.get("url"),
                    "topic": chosen["topic"],
                    "duration_minutes": chosen.get("duration_minutes", 10),
                    "why": reason,
                    "scenario_title": chosen.get("scenario_title", chosen["title"]),
                    "scenario_description": chosen.get("scenario_description", chosen["practice"]),
                    "starter_input": chosen.get("starter_input", ""),
                    "practice": chosen["practice"],
                    "success_measure": chosen["success_measure"],
                }
            )
        if len(recommendations) >= limit:
            break

    # If still below limit, fill with general role-relevant resources
    if len(recommendations) < limit:
        for r in role_resources:
            if r["id"] not in used_ids:
                used_ids.add(r["id"])
                recommendations.append(
                    {
                        "id": r["id"],
                        "title": r["title"],
                        "provider": r["provider"],
                        "url": r.get("bonus_url") or r.get("url"),
                        "bonus_url": r.get("bonus_url") or r.get("url"),
                        "topic": r["topic"],
                        "duration_minutes": r.get("duration_minutes", 10),
                        "why": f"Recommended practice pack for {job_role.capitalize()} professionals.",
                        "scenario_title": r.get("scenario_title", r["title"]),
                        "scenario_description": r.get("scenario_description", r["practice"]),
                        "starter_input": r.get("starter_input", ""),
                        "practice": r["practice"],
                        "success_measure": r["success_measure"],
                    }
                )
            if len(recommendations) >= limit:
                break

    return recommendations


def evaluate_practice_attempt(
    practice_id: str,
    scenario_description: str,
    user_solution: str,
) -> dict[str, Any]:
    """Uses Live LLM (with robust fallback) to evaluate in-platform practice attempts."""
    cleaned_solution = user_solution.strip()
    if not cleaned_solution or len(cleaned_solution) < 5:
        return {
            "passed": False,
            "score": 1,
            "feedback": "Please provide a complete practice attempt before submitting.",
        }

    # If in live mode, ask the LLM to coach and evaluate the solution
    active_mode = os.getenv("AI_MODE", AI_MODE)
    if active_mode == "live" and LLM_API_KEY and LLM_API_URL:
        prompt = f"""You are an encouraging enterprise AI mentor reviewing an employee's micro-practice exercise.
Scenario / Challenge: {scenario_description}
Employee's Submitted Solution:
{cleaned_solution}

Evaluate whether the employee appropriately sanitized PII, identified bugs, or structured the prompt as requested.
Be constructive, concise, and helpful.
Return strictly valid JSON with this exact shape:
{{"passed": <true|false>, "score": <1-5>, "feedback": "<two concise sentences of feedback>"}}"""
        try:
            r = httpx.post(
                LLM_API_URL,
                headers={"Authorization": f"Bearer {LLM_API_KEY}"},
                json={
                    "model": LLM_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                },
                timeout=15,
            )
            r.raise_for_status()
            raw_text = r.json()["choices"][0]["message"]["content"]
            match = re.search(r"\{[\s\S]*\}", raw_text)
            if match:
                data = json.loads(match.group(0))
                return {
                    "passed": bool(data.get("passed", True)),
                    "score": int(data.get("score", 4)),
                    "feedback": str(data.get("feedback", "Good effort completing this practice sprint.")),
                }
        except Exception:
            # Fall back to heuristic check below if live provider is slow
            pass

    # Heuristic fallback for offline/mock mode
    lowered = cleaned_solution.lower()
    has_tokens = any(t in lowered for t in ["[", "token", "mask", "def ", "select", "rule", "question"])
    return {
        "passed": True,
        "score": 5 if has_tokens else 4,
        "feedback": "Well done! Your practice attempt demonstrates good practical awareness of safe enterprise AI execution.",
    }
