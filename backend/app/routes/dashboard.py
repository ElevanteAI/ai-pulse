from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..db import get_db
from .. import models
from ..auth import require_admin
from ..config import MIN_GROUP_SIZE
from ..services import aggregation as agg, policy_check

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

OTHER_TEAMS = "Other teams"


def group(name, people, employees=None, merged=None):
    return {
        "department": name,
        "employees": employees,
        "status": "shown",
        **agg.summarise(people),
        "top_risks": agg.risk_counts(people)[:3],
        "policy_reality": policy_check.for_group(people),
        **({"includes": merged} if merged else {}),
    }


@router.get("")
def org_dashboard(m: models.Membership = Depends(require_admin), db: Session = Depends(get_db)):
    """Leadership view. No group with fewer than MIN_GROUP_SIZE respondents is ever shown on its own.

    1. Departments with >= MIN_GROUP_SIZE respondents are shown individually.
    2. Smaller departments (and respondents with no department) are pooled into "Other teams".
    3. If that pool is still too small, those people are left out of EVERY number on the page,
       including the overall figures. Otherwise "overall minus visible teams" would reveal them.
    """
    # The org always comes from the caller's token-selected membership, never from the request.
    org = m.org
    headcount = dict(
        db.query(models.Membership.department_id, func.count())
        .filter(models.Membership.org_id == org.id)
        .group_by(models.Membership.department_id)
        .all()
    )
    by_dept = agg.respondents_by_department(db, org.id)

    groups, notes = [], []
    included = []  # everyone who ends up inside a shown group; the ONLY people overall figures use
    pooled, pooled_names = [], []
    for dept in sorted(org.departments, key=lambda d: d.name):
        people = by_dept.get(dept.id, [])
        if len(people) >= MIN_GROUP_SIZE:
            groups.append(group(dept.name, people, headcount.get(dept.id, 0)))
            included += people
        elif people:
            pooled += people
            pooled_names.append(dept.name)
            notes.append({"department": dept.name, "employees": headcount.get(dept.id, 0), "status": "pooled"})
        else:
            notes.append({"department": dept.name, "employees": headcount.get(dept.id, 0), "status": "no_responses"})
    pooled += by_dept.get(None, [])  # respondents not assigned to a department

    some_hidden = False
    if len(pooled) >= MIN_GROUP_SIZE:
        groups.append(group(OTHER_TEAMS, pooled, merged=pooled_names + (["No department"] if None in by_dept else [])))
        included += pooled
    else:
        # Say *that* some answers are hidden, never how many: a count of 1 next to a
        # 2-person team would reveal who took part.
        some_hidden = bool(pooled)
        for n in notes:
            if n["status"] == "pooled":
                n["status"] = "hidden"

    enough = len(included) >= MIN_GROUP_SIZE

    return {
        "organization": org.name,
        "min_group_size": MIN_GROUP_SIZE,
        "overall": agg.summarise(included) if enough else None,
        "groups": groups,
        "not_shown": notes,
        "some_responses_hidden": some_hidden,
        "top_risks": agg.risk_counts(included)[:5] if enough else [],
        "ai_scoring": agg.ai_scoring_health(included) if enough else None,
        "policy_reality": policy_check.for_group(included) if enough else None,
    }
