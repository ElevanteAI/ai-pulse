from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from .. import models
from ..auth import current_membership
from ..services.questions import questions_for, load_questions
from ..services.scoring import score_open_answer

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
    bank = {q["id"]: q for q in load_questions()}
    # Resubmitting replaces earlier answers to the same questions instead of duplicating them
    db.query(models.Response).filter(
        models.Response.membership_id == m.id,
        models.Response.question_id.in_([a.question_id for a in body.answers]),
    ).delete(synchronize_session=False)
    for a in body.answers:
        q = bank.get(a.question_id)
        if not q:
            raise HTTPException(400, f"Unknown question {a.question_id}")
        resp = models.Response(membership_id=m.id, question_id=q["id"], answer=a.answer)
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
        db.add(resp)
    db.commit()
    return {"saved": len(body.answers)}
