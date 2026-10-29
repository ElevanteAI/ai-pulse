import re

import httpx

from . import llm
from .questions import questions_for
from .scoring import ALLOWED_FLAGS, parse_json_reply


def safe_text(value, limit):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Expected nonempty text")
    value = " ".join(value.split())
    forbidden = r"https?://|www\.|[<>@]|\b(ignore|bypass|disable|upload|paste|share|send)\b.{0,60}\b(policy|policies|secret|password|customer|confidential|private|data)\b"
    if re.search(forbidden, value, re.IGNORECASE):
        raise ValueError("Unsafe suggestion")
    value = re.sub(r"[^\x20-\x7E]", "", value).strip()
    if not value:
        raise ValueError("Empty suggestion")
    return value[:limit].rstrip()


def validate_suggestions(raw):
    data = parse_json_reply(raw)
    if not isinstance(data, list) or len(data) != 3:
        raise ValueError("Expected exactly three suggestions")
    result = []
    for item in data:
        if not isinstance(item, dict):
            raise ValueError("Expected suggestion object")
        title = safe_text(item.get("title"), 60)
        action = safe_text(item.get("action"), 240)
        action = re.split(r"(?<=[.!?])\s+", action)[0][:239].rstrip(".!?") + "."
        result.append({"title": title, "action": action})
    return result


def suggestion_data(role, seniority, rows):
    questions = {q["id"]: q for q in questions_for(role, seniority)}
    responses = []
    for row in rows:
        question = questions.get(row.question_id)
        if not question:
            continue
        item = {"question_id": row.question_id, "score": row.score, "flags": sorted(set(row.flags or []) & ALLOWED_FLAGS)}
        if question["type"] == "mcq" and row.answer in {option["text"] for option in question["options"]}:
            item["selected_option"] = row.answer
        responses.append(item)
    return {"role": role, "seniority": seniority, "responses": responses}


def improvement_suggestions(role, seniority, rows, fallback_actions):
    if not rows:
        return {"suggestions": [], "source": "none"}
    data = suggestion_data(role, seniority, rows)
    for attempt in range(2):
        try:
            return {"suggestions": validate_suggestions(llm.suggest_improvements(data)), "source": "ai"}
        except (ValueError, TypeError, KeyError, IndexError, httpx.HTTPError):
            continue
    return {"suggestions": [{"title": f"Next step {index}", "action": action} for index, action in enumerate(fallback_actions, 1)], "source": "static"}
