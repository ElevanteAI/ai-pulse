from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from .. import models
from ..auth import current_membership
from ..services.questions import questions_for
from ..services.scoring import ScoringError, score_open_answer

router = APIRouter(prefix="/diagnostic", tags=["diagnostic"])


class AnswerIn(BaseModel):
    question_id: str
    answer: str


class SubmitIn(BaseModel):
    answers: list[AnswerIn]


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
    assigned_questions = questions_for(m.job_role, m.seniority)
    bank = {q["id"]: q for q in assigned_questions}
    answer_ids = [answer.question_id for answer in body.answers]
    expected_ids = set(bank)
    if len(answer_ids) != len(set(answer_ids)):
        raise HTTPException(400, "Each question can be answered only once")
    if set(answer_ids) != expected_ids:
        raise HTTPException(400, "Submit one non-empty answer for every assigned question")

    prepared = []
    for a in body.answers:
        q = bank.get(a.question_id)
        if not q:
            raise HTTPException(400, "Question is not assigned to this user")
        if not a.answer.strip():
            raise HTTPException(400, "Answers cannot be blank")
        result = {"score": None, "reason": None, "flags": []}
        if q["type"] == "mcq":
            option = next((o for o in q["options"] if o["text"] == a.answer), None)
            if option is None:
                raise HTTPException(400, "Invalid answer option")
            result["score"] = option["points"]
        else:
            try:
                result = score_open_answer(q["text"], a.answer)
            except ScoringError:
                raise HTTPException(502, "AI scoring is temporarily unavailable; no answers were saved")
        prepared.append((q, a.answer, result))

    assessment = models.Assessment(membership_id=m.id, status="completed")
    db.add(assessment)
    db.flush()
    for q, answer, result in prepared:
        db.add(models.Response(
            assessment_id=assessment.id,
            membership_id=m.id,
            question_id=q["id"],
            answer=answer,
            score=result["score"],
            reason=result["reason"],
            flags=result["flags"],
        ))
    db.commit()
    return {"saved": len(prepared), "assessment_id": assessment.id}
