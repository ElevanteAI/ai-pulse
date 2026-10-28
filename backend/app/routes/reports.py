import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from .. import models
from ..auth import current_membership
from ..utils import maturity_level
from ..services.questions import load_questions

router = APIRouter(prefix="/reports", tags=["reports"])
log = logging.getLogger(__name__)

NEXT_STEPS = {
    "support": ["Use AI to draft first replies, then edit", "Summarise long ticket threads before escalating", "Never paste customer details into public chatbots"],
    "engineering": ["Use a code assistant for tests and refactors", "Review every AI suggestion before merging", "Keep secrets and customer data out of prompts"],
    "sales": ["Draft outreach emails with AI and personalise them", "Summarise call notes into CRM updates", "Check AI-written claims before sending"],
    "manager": ["Agree an AI usage policy with your team", "Pick one workflow per quarter to improve with AI", "Track time saved, not tool licences"],
}


@router.get("/me")
def my_report(m: models.Membership = Depends(current_membership), db: Session = Depends(get_db)):
    rows = db.query(models.Response).filter_by(membership_id=m.id).all()
    scores = [r.score for r in rows if r.score is not None]
    avg = sum(scores) / len(scores) if scores else None
    flags = sorted({f for r in rows for f in (r.flags or [])})
    texts = {q["id"]: q["text"] for q in load_questions()}
    # Be explicit about which parts of the result came from AI, and why
    ai_assessments = [
        {
            "question": texts.get(r.question_id, r.question_id),
            "status": r.ai_status,
            "score": r.score,
            "reason": r.reason,
            "flags": r.flags or [],
            "scored_by": r.scored_by,
        }
        for r in rows if r.ai_status
    ]
    return {
        "name": m.user.name,
        "organization": m.org.name,
        "answered": len(rows),
        "average_score": round(avg, 2) if avg is not None else None,
        "level": maturity_level(avg),
        "risks": flags,
        "ai_assessments": ai_assessments,
        "next_steps": NEXT_STEPS.get(m.job_role, NEXT_STEPS["manager"]),
    }


@router.delete("/me")
def delete_my_data(m: models.Membership = Depends(current_membership), db: Session = Depends(get_db)):
    """Right to delete: removes all of the caller's answers (and so their report) in the selected org.

    Hard delete, not a soft-delete flag. Dashboards are computed live from these rows,
    so the person disappears from every dashboard on the next request. Answers in the
    user's other organizations are untouched; each org's data is deleted from inside that org.
    """
    deleted = db.query(models.Response).filter_by(membership_id=m.id).delete()
    db.commit()
    # Record that a deletion happened, never what was deleted
    log.info("Data deletion: membership=%s org=%s rows=%s", m.id, m.org_id, deleted)
    return {"deleted_answers": deleted}
