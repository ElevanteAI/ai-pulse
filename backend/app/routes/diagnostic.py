from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.dialects.sqlite import insert

from ..db import get_db
from .. import models
from ..auth import current_membership
from ..services.questions import questions_for
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
    return [
        {k: v for k, v in q.items() if k != "points"} | (
            {"options": [o["text"] for o in q["options"]]} if q["type"] == "mcq" else {}
        )
        for q in qs
    ]


@router.post("/submit")
def submit(body: SubmitIn, m: models.Membership = Depends(current_membership), db: Session = Depends(get_db)):
    bank = {q["id"]: q for q in questions_for(m.job_role, m.seniority)}
    question_ids = [a.question_id for a in body.answers]
    if len(question_ids) != len(set(question_ids)):
        raise HTTPException(400, "Duplicate question in submission")
    results = []
    for a in body.answers:
        q = bank.get(a.question_id)
        if not q:
            raise HTTPException(400, f"Question not assigned: {a.question_id}")
        if not a.answer.strip():
            raise HTTPException(400, "Answers cannot be empty")
        result = {"membership_id": m.id, "question_id": q["id"], "answer": a.answer, "reason": None, "flags": []}
        if q["type"] == "mcq":
            option = next((o for o in q["options"] if o["text"] == a.answer), None)
            if option is None:
                raise HTTPException(400, f"Invalid option for {q['id']}")
            result["score"] = option["points"]
        else:
            result.update(score_open_answer(q["text"], a.answer))
        results.append(result)
    for result in results:
        statement = insert(models.Response).values(**result)
        statement = statement.on_conflict_do_update(
            index_elements=["membership_id", "question_id"],
            set_={key: statement.excluded[key] for key in ("answer", "score", "reason", "flags")},
        )
        db.execute(statement)
    db.commit()
    return {"saved": len(body.answers)}
