import json
import re

import httpx

from . import llm

ALLOWED_FLAGS = {"customer_data_shared", "confidential_data_shared", "unreviewed_output", "policy_unaware"}
UNSCORED = {"score": None, "reason": "AI scoring unavailable; this answer is unscored.", "flags": []}


def parse_json_reply(raw):
    if not isinstance(raw, str) or len(raw) > 20000:
        raise ValueError("Invalid AI reply")
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.IGNORECASE)
    return json.loads(cleaned)


def validate_score(raw):
    data = parse_json_reply(raw)
    if not isinstance(data, dict):
        raise ValueError("Expected an object")
    score = data.get("score")
    if type(score) is not int or not 1 <= score <= 5:
        raise ValueError("Score must be an integer from 1 to 5")
    flags = data.get("flags", [])
    if not isinstance(flags, list) or any(not isinstance(flag, str) for flag in flags):
        raise ValueError("Flags must be a list of strings")
    reason = data.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        reason = "No explanation provided."
    return {"score": score, "reason": reason.strip()[:500], "flags": sorted(set(flags) & ALLOWED_FLAGS)}


def score_open_answer(question_text: str, answer: str) -> dict:
    for attempt in range(2):
        try:
            return validate_score(llm.score_answer(question_text, answer))
        except (ValueError, TypeError, KeyError, IndexError, httpx.HTTPError):
            continue
    return dict(UNSCORED)
