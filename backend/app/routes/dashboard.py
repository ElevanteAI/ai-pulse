from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..db import get_db
from .. import models
from ..auth import require_admin
from ..services import aggregation as agg

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
def org_dashboard(m: models.Membership = Depends(require_admin), db: Session = Depends(get_db)):
    # The org always comes from the caller's token-selected membership, never from the request.
    org = m.org
    headcount = {
        dept_id: n for dept_id, n in
        db.query(models.Membership.department_id, func.count())
        .filter(models.Membership.org_id == org.id)
        .group_by(models.Membership.department_id)
    }
    by_dept = agg.respondents_by_department(db, org.id)

    departments = []
    for dept in sorted(org.departments, key=lambda d: d.name):
        people = by_dept.get(dept.id, [])
        departments.append({"department": dept.name, "employees": headcount.get(dept.id, 0)} | agg.summarise(people))

    everyone = [p for people in by_dept.values() for p in people]
    return {
        "organization": org.name,
        "overall": agg.summarise(everyone),
        "departments": departments,
        "top_risks": agg.risk_counts(everyone)[:5],
        "ai_scoring": agg.ai_scoring_health(everyone),
    }
