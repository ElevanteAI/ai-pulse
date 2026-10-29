from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from .. import models
from ..auth import current_membership
from ..utils import maturity_level
from ..audit import record

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

MIN_GROUP_SIZE = 5  # client requirement: no scores or risks for groups smaller than this
SUPPRESSED_LEVEL = "Not enough responses"


@router.get("")
def org_dashboard(org_id: int, m: models.Membership = Depends(current_membership), db: Session = Depends(get_db)):
    if m.role != "admin":
        raise HTTPException(403, "Admins only")

    # Tenant check first so callers can't probe which org IDs exist
    if org_id != m.org_id:
        raise HTTPException(403, "You cannot access another organization")

    org = db.get(models.Organization, org_id)
    if not org:
        raise HTTPException(404, "Organization not found")

    record(db, m, "dashboard_view")
    db.commit()

    members = db.query(models.Membership).filter_by(org_id=org_id).all()

    # Per-department tallies. Flags are kept per group so small groups can be dropped.
    groups = []
    for dept in org.departments:
        dept_members = [x for x in members if x.department_id == dept.id]
        employee_avgs = []  # one average per employee who completed the diagnostic
        responded = 0
        flags = {}
        for dm in dept_members:
            rows = db.query(models.Response).filter_by(membership_id=dm.id).all()
            if rows:
                responded += 1
            scores = [r.score for r in rows if r.score is not None]
            if scores:
                employee_avgs.append(sum(scores) / len(scores))
            for r in rows:
                for f in r.flags or []:
                    flags[f] = flags.get(f, 0) + 1
        groups.append({"name": dept.name, "employees": len(dept_members), "responded": responded,
                       "employee_avgs": employee_avgs, "flags": flags})

    # Privacy: groups under MIN_GROUP_SIZE respondents are only ever shown pooled as "Other teams"
    big = [g for g in groups if g["responded"] >= MIN_GROUP_SIZE]
    small = [g for g in groups if g["responded"] < MIN_GROUP_SIZE]
    reported = list(big)
    if small:
        pooled_flags = {}
        for g in small:
            for f, n in g["flags"].items():
                pooled_flags[f] = pooled_flags.get(f, 0) + n
        reported.append({
            "name": "Other teams",
            "employees": sum(g["employees"] for g in small),
            "responded": sum(g["responded"] for g in small),
            "employee_avgs": [a for g in small for a in g["employee_avgs"]],
            "flags": pooled_flags,
        })

    departments = []
    all_flags = {}
    visible_avgs = []  # company level uses only groups we are allowed to show
    for g in reported:
        if g["responded"] < MIN_GROUP_SIZE:
            # Even pooled, too few people: show headcount only, no scores or risks
            departments.append({
                "department": g["name"],
                "employees": g["employees"],
                "responded": g["responded"],
                "average_score": None,
                "level": SUPPRESSED_LEVEL,
                "suppressed": True,
            })
            continue
        avgs = g["employee_avgs"]
        visible_avgs.extend(avgs)
        avg = sum(avgs) / len(avgs) if avgs else None
        departments.append({
            "department": g["name"],
            "employees": g["employees"],
            "responded": g["responded"],
            "average_score": round(avg, 2) if avg is not None else None,
            "level": maturity_level(avg),
            "suppressed": False,
        })
        for f, n in g["flags"].items():
            all_flags[f] = all_flags.get(f, 0) + n

    # Counts are safe to total; the average excludes suppressed groups so it can't be used
    # to back out a small group's score.
    company_avg = sum(visible_avgs) / len(visible_avgs) if visible_avgs else None
    return {
        "organization": org.name,
        "totals": {
            "headcount": sum(g["employees"] for g in groups),
            "completed": sum(g["responded"] for g in groups),
            "average_score": round(company_avg, 2) if company_avg is not None else None,
            "level": maturity_level(company_avg),
        },
        "departments": departments,
        "top_risks": sorted(all_flags.items(), key=lambda kv: -kv[1])[:5],
    }
