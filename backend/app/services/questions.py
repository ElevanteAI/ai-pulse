import json
import os

_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "questions.json")
SENIORITY_RANK = {"junior": 0, "mid": 1, "senior": 2, "lead": 3}


def load_questions():
    with open(_PATH) as f:
        return json.load(f)


def questions_for(job_role: str, seniority: str):
    result = []
    for q in load_questions():
        if q["roles"] != ["all"] and job_role not in q["roles"]:
            continue
        if SENIORITY_RANK[seniority] < SENIORITY_RANK[q.get("min_seniority", "junior")]:
            continue
        result.append(q)
    return result
