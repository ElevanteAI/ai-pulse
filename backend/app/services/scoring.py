import json
import logging

from . import llm

logger = logging.getLogger(__name__)

# Allowed risk flags
ALLOWED_FLAGS = {"customer_data_shared", "confidential_data_shared", "unreviewed_output", "policy_unaware"}


def score_open_answer(question_text: str, answer: str) -> dict:
    """Score an open-ended answer using LLM. Returns safe, validated score data."""
    try:
        raw = llm.score_answer(question_text, answer)
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response: {e}. Raw: {raw[:200]}")
        return {"score": 3, "reason": "Assessment failed", "flags": []}
    except Exception as e:
        logger.error(f"Unexpected error in score_open_answer: {e}")
        return {"score": 3, "reason": "Assessment failed", "flags": []}
    
    # Validate score is numeric and in range [1, 5]
    try:
        score = data.get("score")
        if not isinstance(score, (int, float)):
            logger.warning(f"Invalid score type: {type(score)}. Using default.")
            score = 3
        else:
            # Clamp score to valid range
            score = max(1, min(5, int(score)))
    except (TypeError, ValueError) as e:
        logger.error(f"Failed to validate score: {e}")
        score = 3
    
    # Validate reason is string and truncate if needed
    reason = data.get("reason", "")
    if not isinstance(reason, str):
        reason = str(reason)
    reason = reason[:500]  # Truncate to 500 chars max
    
    # Validate flags are in allowed set
    flags = data.get("flags", [])
    if not isinstance(flags, list):
        logger.warning(f"Flags not a list: {type(flags)}")
        flags = []
    else:
        # Filter to only allowed flags
        flags = [f for f in flags if f in ALLOWED_FLAGS]
    
    return {"score": score, "reason": reason, "flags": flags}
