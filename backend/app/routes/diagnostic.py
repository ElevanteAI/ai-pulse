from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import get_db
from .. import models
from ..auth import current_membership
from ..services.questions import questions_for
from ..services.scoring import score_open_answer

router = APIRouter(prefix="/diagnostic", tags=["diagnostic"])

MAX_ANSWER_CHARS = 2000


class AnswerIn(BaseModel):
    question_id: str = Field(max_length=40)
    answer: str = Field(min_length=1, max_length=MAX_ANSWER_CHARS)


class SubmitIn(BaseModel):
    answers: list[AnswerIn] = Field(max_length=50)


@router.get("/questions")
def get_questions(m: models.Membership = Depends(current_membership)):
    qs = questions_for(m.job_role, m.seniority)
    # don't leak scoring points to the client
    return [
        {k: v for k, v in q.items() if k != "points"} | (
            {"options": [o["text"] for o in q["options"]]} if q["type"] == "mcq" else {}
        )
        for q in qs
    ]


@router.post("/submit")
def submit(body: SubmitIn, m: models.Membership = Depends(current_membership), db: Session = Depends(get_db)):
    # The user must answer exactly the questions assigned to their role and seniority, once each.
    assigned = {q["id"]: q for q in questions_for(m.job_role, m.seniority)}
    submitted = [a.question_id for a in body.answers]
    if len(submitted) != len(set(submitted)):
        raise HTTPException(400, "Each question can only be answered once")
    if unknown := set(submitted) - assigned.keys():
        raise HTTPException(400, f"Not your questions: {sorted(unknown)}")
    if missing := assigned.keys() - set(submitted):
        raise HTTPException(400, f"Please answer every question. Missing: {sorted(missing)}")

    new_rows = []
    for a in body.answers:
        q = assigned[a.question_id]
        resp = models.Response(membership_id=m.id, question_id=q["id"], answer=a.answer.strip())
        if q["type"] == "mcq":
            option = next((o for o in q["options"] if o["text"] == a.answer), None)
            if option is None:
                raise HTTPException(400, f"Invalid option for {q['id']}")
            resp.score = option["points"]
        else:
            result = score_open_answer(q["text"], a.answer)
            resp.score = result["score"]
            resp.reason = result["reason"]
            resp.flags = result["flags"]
            resp.ai_status = result["status"]
            resp.scored_by = result["model"]
        new_rows.append(resp)

    # Retaking the diagnostic replaces the previous answers (one current result per person per org).
    # Scoring happens above, before anything is deleted, so a failure can't lose the old result.
    db.query(models.Response).filter_by(membership_id=m.id).delete()
    db.add_all(new_rows)
    db.commit()
    return {"saved": len(new_rows)}
