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
    4. Teams not shown on their own are listed by name only. Whether one has 0 or 4 respondents
       must look the same, or a 1-person team shows who took part (and later, who deleted).
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

    groups, not_shown = [], []
    included = []  # everyone who ends up inside a shown group; the ONLY people overall figures use
    pooled = []
    for dept in sorted(org.departments, key=lambda d: d.name):
        people = by_dept.get(dept.id, [])
        if len(people) >= MIN_GROUP_SIZE:
            groups.append(group(dept.name, people, headcount.get(dept.id, 0)))
            included += people
        else:
            pooled += people
            not_shown.append(dept.name)
    pooled += by_dept.get(None, [])  # respondents not assigned to a department
    # Based on membership, not on who answered, so it doesn't change when someone answers or deletes
    covers = not_shown + (["No department"] if None in headcount else [])

    pool_shown = len(pooled) >= MIN_GROUP_SIZE
    if pool_shown:
        groups.append(group(OTHER_TEAMS, pooled, merged=covers))
        included += pooled

    enough = len(included) >= MIN_GROUP_SIZE

    return {
        "organization": org.name,
        "min_group_size": MIN_GROUP_SIZE,
        "overall": agg.summarise(included) if enough else None,
        "groups": groups,
        "not_shown": [{"department": name} for name in not_shown],
        # Whether small teams are left out, never whether anyone in them answered
        "small_teams_left_out": bool(covers) and not pool_shown,
        "top_risks": agg.risk_counts(included)[:5] if enough else [],
        "ai_scoring": agg.ai_scoring_health(included) if enough else None,
        "policy_reality": policy_check.for_group(included) if enough else None,
    }
