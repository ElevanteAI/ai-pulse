from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from .. import models
from ..auth import current_membership
from ..config import MIN_GROUP_SIZE
from ..utils import maturity_level

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# One definition of the maturity levels, shared with the personal report
level_for = maturity_level


def average_score(scores):
    """Mean of the scored answers, or None when nothing has been scored yet."""
    return sum(scores) / len(scores) if scores else None


def _group_row(name, employees, responded, scores):
    """One dashboard row. Groups below MIN_GROUP_SIZE respondents get no scores."""
    if responded < MIN_GROUP_SIZE:
        return {
            "department": name,
            "employees": employees,
            "responded": None,
            "average_score": None,
            "level": "Not enough responses",
            "suppressed": True,
        }
    avg = average_score(scores)
    return {
        "department": name,
        "employees": employees,
        "responded": responded,
        "average_score": round(avg, 2) if avg is not None else None,
        "level": level_for(avg),
        "suppressed": False,
    }


@router.get("")
def org_dashboard(org_id: int, m: models.Membership = Depends(current_membership), db: Session = Depends(get_db)):
    if m.role != "admin":
        raise HTTPException(403, "Admins only")
    # org_id comes from the client; the organization the caller is admin of comes from the token
    if org_id != m.org_id:
        raise HTTPException(403, "Not your organization")

    org = db.get(models.Organization, m.org_id)
    members = db.query(models.Membership).filter_by(org_id=org.id).all()

    all_flags = {}
    total_responded = 0
    shown, other = [], {"employees": 0, "responded": 0, "scores": []}
    for dept in org.departments:
        dept_members = [x for x in members if x.department_id == dept.id]
        scores = []
        responded = 0
        flags = {}
        for dm in dept_members:
            rows = db.query(models.Response).filter_by(membership_id=dm.id).all()
            if rows:
                responded += 1
            for r in rows:
                if r.score is not None:
                    scores.append(r.score)
                for f in r.flags or []:
                    flags[f] = flags.get(f, 0) + 1
        total_responded += responded
        for f, n in flags.items():
            all_flags[f] = all_flags.get(f, 0) + n

        if responded >= MIN_GROUP_SIZE:
            shown.append(_group_row(dept.name, len(dept_members), responded, scores))
        else:
            # Too small to show alone: fold into "Other teams"
            other["employees"] += len(dept_members)
            other["responded"] += responded
            other["scores"] += scores

    if other["employees"]:
        # Still hidden if even the combined group is too small
        shown.append(_group_row("Other teams", other["employees"], other["responded"], other["scores"]))

    return {
        "organization": org.name,
        "departments": shown,
        # Risk counts could point at one person when very few people answered
        "top_risks": sorted(all_flags.items(), key=lambda kv: -kv[1])[:5] if total_responded >= MIN_GROUP_SIZE else [],
    }
