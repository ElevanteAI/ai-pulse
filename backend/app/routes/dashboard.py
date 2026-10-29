from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from .. import models
from ..auth import current_membership
from ..utils import maturity_level
from ..services.questions import questions_for

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
MIN_COMPLETERS = 5


def department_statistics(members, db):
    averages = []
    flags = {}
    for member in members:
        rows = db.query(models.Response).filter_by(membership_id=member.id).all()
        assigned = {q["id"] for q in questions_for(member.job_role, member.seniority)}
        answered = {row.question_id for row in rows if row.answer.strip()}
        if not assigned or not assigned <= answered:
            continue
        scores = [row.score for row in rows if row.question_id in assigned and row.score is not None]
        averages.append(sum(scores) / len(scores) if scores else None)
        for row in rows:
            if row.question_id in assigned:
                for flag in row.flags or []:
                    flags[flag] = flags.get(flag, 0) + 1
    scored_averages = [avg for avg in averages if avg is not None]
    average = sum(scored_averages) / len(scored_averages) if scored_averages else None
    return {
        "employees": len(members),
        "responded": len(averages),
        "average_score": round(average, 2) if average is not None else None,
        "level": maturity_level(average),
    }, flags


@router.get("")
def org_dashboard(m: models.Membership = Depends(current_membership), db: Session = Depends(get_db)):
    if m.role != "admin":
        raise HTTPException(403, "Admins only")

    org = db.get(models.Organization, m.org_id)
    if not org:
        raise HTTPException(404, "Organization not found")

    members = db.query(models.Membership).filter_by(org_id=m.org_id).all()
    departments = []
    all_flags = {}
    small_members = []
    for dept in org.departments:
        dept_members = [x for x in members if x.department_id == dept.id]
        statistics, flags = department_statistics(dept_members, db)
        if statistics["responded"] < MIN_COMPLETERS:
            small_members.extend(dept_members)
            continue
        departments.append({"department": dept.name, "hidden": False, **statistics})
        for flag, count in flags.items():
            all_flags[flag] = all_flags.get(flag, 0) + count
    if small_members:
        statistics, flags = department_statistics(small_members, db)
        if statistics["responded"] >= MIN_COMPLETERS:
            departments.append({"department": "Other teams", "hidden": False, **statistics})
            for flag, count in flags.items():
                all_flags[flag] = all_flags.get(flag, 0) + count
        else:
            departments.append({"department": "Other teams", "hidden": True})

    return {
        "organization": org.name,
        "departments": departments,
        "top_risks": sorted(all_flags.items(), key=lambda kv: -kv[1])[:5],
    }
