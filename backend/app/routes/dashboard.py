from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from .. import models
from ..auth import current_membership

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# Privacy threshold: teams with fewer than this many completed responses are hidden
# to prevent individual identification and protect anonymity per GDPR requirements.
# This constant is reusable across the application for consistent enforcement.
MIN_GROUP_SIZE = 5


def level_for(avg):
    if avg is None:
        return "Not assessed"
    if avg < 1.5:
        return "Beginner"
    if avg < 2.5:
        return "Exploring"
    if avg < 3.5:
        return "Practitioner"
    return "Leader"


@router.get("")
def org_dashboard(org_id: int, m: models.Membership = Depends(current_membership), db: Session = Depends(get_db)):
    if m.role != "admin":
        raise HTTPException(403, "Admins only")

    org = db.get(models.Organization, org_id)
    if not org:
        raise HTTPException(404, "Organization not found")

    members = db.query(models.Membership).filter_by(org_id=org_id).all()
    departments = []
    all_flags = {}
    
    # Calculate response rates for each department
    response_rates = []
    hidden_team_count = 0
    org_completed = 0
    org_invited = 0
    
    for dept in org.departments:
        dept_members = [x for x in members if x.department_id == dept.id]
        scores = []
        responded = 0
        for dm in dept_members:
            rows = db.query(models.Response).filter_by(membership_id=dm.id).all()
            if rows:
                responded += 1
                org_completed += 1
            for r in rows:
                if r.score is not None:
                    scores.append(r.score)
                for f in r.flags or []:
                    all_flags[f] = all_flags.get(f, 0) + 1
        
        invited = len(dept_members)
        org_invited += invited
        
        avg = sum(scores) / len(dept_members) if dept_members else None
        departments.append({
            "department": dept.name,
            "employees": len(dept_members),
            "responded": responded,
            "average_score": round(avg, 2) if avg is not None else None,
            "level": level_for(avg),
        })
        
        # Add to response rates if visible (>= MIN_GROUP_SIZE completed)
        if responded >= MIN_GROUP_SIZE:
            response_rates.append({
                "team_id": dept.id,
                "team_name": dept.name,
                "completed": responded,
                "invited": invited,
            })
        else:
            # Hide teams with fewer than MIN_GROUP_SIZE responses
            hidden_team_count += 1

    return {
        "organization": org.name,
        "departments": departments,
        "top_risks": sorted(all_flags.items(), key=lambda kv: -kv[1])[:5],
        "response_rates": response_rates,
        "hidden_team_count": hidden_team_count,
        "overall": {
            "completed": org_completed,
            "invited": org_invited,
        }
    }
