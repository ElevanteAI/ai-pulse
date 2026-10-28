import json
import re
from typing import Literal

import httpx
from pydantic import BaseModel, Field, StrictInt, ValidationError

from . import llm

RiskFlag = Literal[
    "customer_data_shared",
    "confidential_data_shared",
    "unreviewed_output",
    "policy_unaware",
]


class ScoringError(Exception):
    """A provider response that must not become employee data."""


class ScoredAnswer(BaseModel):
    score: StrictInt = Field(ge=1, le=5)
    reason: str = Field(min_length=1, max_length=500)
    flags: list[RiskFlag] = Field(default_factory=list)


def _json_object(raw: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.IGNORECASE).strip()
    try:
        value = json.loads(cleaned)
    except (TypeError, json.JSONDecodeError) as exc:
        match = re.search(r"\{[\s\S]*\}", raw)
        if match:
            try:
                value = json.loads(match.group(0))
            except Exception:
                raise ScoringError("AI returned invalid JSON") from exc
        else:
            raise ScoringError("AI returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise ScoringError("AI returned an invalid response shape")
    return value


def score_open_answer(question_text: str, answer: str) -> dict:
    try:
        raw = llm.score_answer(question_text, answer)
        data = ScoredAnswer.model_validate(_json_object(raw))
    except ScoringError:
        raise
    except (ValidationError, httpx.HTTPError, KeyError, IndexError, OSError, ValueError) as exc:
        raise ScoringError("AI returned an invalid score") from exc
    return data.model_dump()
