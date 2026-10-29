import json
import logging
import re

from . import llm

log = logging.getLogger(__name__)

ALLOWED_FLAGS = {"customer_data_shared", "confidential_data_shared", "unreviewed_output", "policy_unaware"}
DEFAULT_SCORE = 3
DEFAULT_REASON = "No explanation provided."
FALLBACK_REASON = "Automatic scoring was unavailable; a neutral default score was recorded."

_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}
_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)
_OBJECT = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json(raw: str) -> dict:
    """Parse the model output, tolerating code fences and surrounding prose."""
    text = raw.strip()
    fenced = _FENCE.search(text)
    if fenced:
        text = fenced.group(1).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = _OBJECT.search(text)
        if not match:
            raise
        data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise ValueError("model output is not a JSON object")
    return data


def _clean_score(value) -> float:
    if isinstance(value, str):
        value = _WORDS.get(value.strip().lower(), value)
    score = float(value)  # raises on junk, handled by the caller
    if score != score:  # NaN
        raise ValueError("score is NaN")
    return min(5.0, max(1.0, score))


def _clean_flags(value) -> list:
    if not isinstance(value, list):
        return []
    return sorted({f for f in value if isinstance(f, str) and f in ALLOWED_FLAGS})


def _clean_reason(value) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return DEFAULT_REASON


def score_open_answer(question_text: str, answer: str) -> dict:
    """Never raises: a failing or garbled model response becomes a safe default."""
    try:
        data = _extract_json(llm.score_answer(question_text, answer))
        return {
            "score": _clean_score(data.get("score")),
            "reason": _clean_reason(data.get("reason")),
            "flags": _clean_flags(data.get("flags")),
        }
    except Exception:
        log.exception("Open-answer scoring failed; using default score")
        return {"score": DEFAULT_SCORE, "reason": FALLBACK_REASON, "flags": []}
