import json
import logging
import re
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from . import llm

log = logging.getLogger(__name__)

ALLOWED_FLAGS = {
    "customer_data_shared",
    "confidential_data_shared",
    "unreviewed_output",
    "policy_unaware",
}

# Matches markdown code fences like ```json ... ``` or ``` ... ```
_FENCE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL | re.IGNORECASE)


class ScoreResult(BaseModel):
    score: int = Field(strict=True, ge=1, le=5)
    reason: str = Field(min_length=1, max_length=500)
    flags: list[str] = Field(default_factory=list)


def _extract_json(raw: str) -> Any:
    """Step 1: Parsing - Strip markdown code blocks and parse raw JSON text."""
    text = raw.strip()
    fenced = _FENCE.match(text)
    if fenced:
        text = fenced.group(1)
    return json.loads(text)


def _unscored(reason: str) -> dict:
    """Fallback when AI output is invalid or the model service is down."""
    return {"score": None, "reason": reason, "flags": []}


def score_open_answer(question_text: str, answer: str) -> dict:
    try:
        raw = llm.score_answer(question_text, answer)
        data = _extract_json(raw)                  # Step 1: Parse
        result = ScoreResult.model_validate(data)  # Step 2: Validate
    except (json.JSONDecodeError, ValidationError) as exc:
        log.warning("AI scoring returned an invalid response: %s", type(exc).__name__) 
        return _unscored("Automatic scoring returned an invalid response.")
    except Exception as exc:  # Network error, timeout, LLM outage...
        log.error("AI scoring failed: %s", type(exc).__name__)
        return _unscored("Automatic scoring was unavailable.")

    # Drop hallucinated or unknown flags; keep only allowed rubric flags
    flags = [f for f in dict.fromkeys(result.flags) if f in ALLOWED_FLAGS]
    return {"score": result.score, "reason": result.reason, "flags": flags}
