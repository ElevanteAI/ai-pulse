from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from .. import models
from ..auth import current_membership
from ..utils import average_score, maturity_level

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
MINIMUM_GROUP_SIZE = 5


def _latest_completed(db: Session, membership_id: int):
    return (db.query(models.Assessment).filter_by(membership_id=membership_id, status="completed")
            .order_by(models.Assessment.submitted_at.desc(), models.Assessment.id.desc()).first())


def _summary(name: str, assessments: list[models.Assessment]):
    scores = [average_score(assessment.responses) for assessment in assessments]
    scores = [score for score in scores if score is not None]
    avg = sum(scores) / len(scores) if scores else None
    risks = {}
    for assessment in assessments:
        for flag in {flag for response in assessment.responses for flag in (response.flags or [])}:
            risks[flag] = risks.get(flag, 0) + 1
    return {"department": name, "completed": len(assessments),
            "average_score": round(avg, 2) if avg is not None else None,
            "level": maturity_level(avg), "risks": risks}


@router.get("")
def org_dashboard(m: models.Membership = Depends(current_membership), db: Session = Depends(get_db)):
    if m.role != "admin":
        raise HTTPException(403, "Admins only")

    org = m.org  # The tenant comes from the verified token, never a browser parameter.
    departments = []
    suppressed_assessments = []
    for department in org.departments:
        memberships = db.query(models.Membership).filter_by(org_id=org.id, department_id=department.id).all()
        assessments = [assessment for member in memberships if (assessment := _latest_completed(db, member.id))]
        if len(assessments) >= MINIMUM_GROUP_SIZE:
            departments.append(_summary(department.name, assessments))
        else:
            suppressed_assessments.extend(assessments)

    if len(suppressed_assessments) >= MINIMUM_GROUP_SIZE:
        departments.append(_summary("Other teams", suppressed_assessments))

    all_risks = {}
    for department in departments:
        for flag, count in department.pop("risks").items():
            all_risks[flag] = all_risks.get(flag, 0) + count
    return {"organization": org.name, "minimum_group_size": MINIMUM_GROUP_SIZE,
            "departments": departments,
            "top_risks": sorted(all_risks.items(), key=lambda item: (-item[1], item[0]))[:5]}
