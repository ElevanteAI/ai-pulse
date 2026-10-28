import json
import os
from functools import lru_cache

_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "questions.json")

# Seniority is ordered by rank, not alphabetically ("lead" < "mid" as strings!)
SENIORITY_RANK = {"junior": 0, "mid": 1, "senior": 2, "lead": 3}


@lru_cache(maxsize=1)
def load_questions():
    with open(_PATH, encoding="utf-8") as f:
        return json.load(f)


def questions_for(job_role: str, seniority: str):
    """Common questions for everyone + questions for this job role, filtered by seniority."""
    if seniority not in SENIORITY_RANK:
        raise ValueError(f"Unknown seniority {seniority!r}")
    rank = SENIORITY_RANK[seniority]
    result = []
    for q in load_questions():
        if q["roles"] != ["all"] and job_role not in q["roles"]:
            continue
        if rank < SENIORITY_RANK[q.get("min_seniority", "junior")]:
            continue
        result.append(q)
    return result
