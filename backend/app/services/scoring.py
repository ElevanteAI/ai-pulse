"""Turns the model's raw reply into a score we're willing to store, or refuses to.

The model is treated as an untrusted input. Anything that doesn't match the contract
becomes status="needs_review" with score=None, which is excluded from every average.
We never clamp, guess or "fix" a bad score; we'd rather have no number than a wrong one.
"""
import json
import logging
import re

from . import llm

log = logging.getLogger(__name__)

ALLOWED_FLAGS = {"customer_data_shared", "confidential_data_shared", "unreviewed_output", "policy_unaware"}
SCORED, NEEDS_REVIEW = "scored", "needs_review"

# Cheap defence-in-depth against prompt injection. If the answer talks to the scorer,
# we don't trust whatever score comes back for it.
_INJECTION = re.compile(
    r"ignore (all |the |any )?(previous|prior|above)|system prompt|you are now|"
    r"(give|return|output|assign) (me |this )?(a )?(score|rating)|score (of |= ?|: ?)?5\b",
    re.IGNORECASE,
)


def _needs_review(problem: str) -> dict:
    return {"score": None, "reason": None, "flags": [], "status": NEEDS_REVIEW, "problem": problem}


def _extract_json(raw: str):
    """Accept bare JSON, or JSON wrapped in ``` fences / surrounding prose. Return a dict or None."""
    if not isinstance(raw, str):
        return None
    start = raw.find("{")
    if start == -1:
        return None
    try:
        obj, _ = json.JSONDecoder().raw_decode(raw[start:])
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _valid_score(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        n = value
    elif isinstance(value, float) and value.is_integer():
        n = int(value)
    elif isinstance(value, str) and value.strip().isdigit():
        n = int(value.strip())
    else:
        return None  # "four", 3.5, None, lists...
    return n if 1 <= n <= 5 else None


def parse_model_output(raw: str) -> dict:
    data = _extract_json(raw)
    if data is None:
        return _needs_review("reply was not JSON")

    score = _valid_score(data.get("score"))
    if score is None:
        return _needs_review(f"score {data.get('score')!r} is not an integer from 1 to 5")

    reason = data.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        return _needs_review("no reason given")

    flags = data.get("flags")
    if not isinstance(flags, list):
        return _needs_review("flags missing")
    if not all(isinstance(f, str) for f in flags):
        return _needs_review("flags must be a list of labels")
    unknown = [f for f in flags if f not in ALLOWED_FLAGS]
    if unknown:
        # Never show leadership a label the model invented about a person (e.g. "probably_lying")
        log.warning("Dropped unknown flags from model output: %s", unknown)

    return {
        "score": score,
        "reason": reason.strip()[:300],
        "flags": sorted({f for f in flags if f in ALLOWED_FLAGS}),
        "status": SCORED,
        "problem": f"dropped unknown flags {unknown}" if unknown else None,
    }


def score_open_answer(question_text: str, answer: str) -> dict:
    """Never raises. Returns score/reason/flags/status/problem/model."""
    model = llm.model_name()
    if _INJECTION.search(answer):
        return _needs_review("answer contains instructions aimed at the scorer") | {"model": model}

    result = _needs_review("not attempted")
    for attempt in range(2):  # one retry: live models are occasionally malformed or time out
        try:
            result = parse_model_output(llm.score_answer(question_text, answer))
        except llm.LLMError as e:
            log.warning("LLM call failed (attempt %d): %s", attempt + 1, e)
            result = _needs_review("AI service unavailable")
        if result["status"] == SCORED:
            break
    return result | {"model": model}
