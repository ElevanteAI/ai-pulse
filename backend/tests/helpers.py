from app.services.questions import questions_for


def full_answers(job_role, seniority, mcq_choice=-1, open_text="I used AI to draft a report and checked every figure."):
    """A valid submission answering every assigned question. mcq_choice indexes into each question's options."""
    out = []
    for q in questions_for(job_role, seniority):
        if q["type"] == "mcq":
            out.append({"question_id": q["id"], "answer": q["options"][mcq_choice]["text"]})
        else:
            out.append({"question_id": q["id"], "answer": open_text})
    return out
