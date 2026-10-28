"""Turning individual results into group numbers for leadership.

Rule of thumb: average per person first, then across people. Otherwise someone with more
answers counts for more, and people who never responded drag the number down.
"""
from collections import defaultdict
from statistics import mean

from sqlalchemy.orm import Session

from .. import models
from ..utils import maturity_level


def person_average(rows):
    scores = [r.score for r in rows if r.score is not None]
    return mean(scores) if scores else None


def respondents_by_department(db: Session, org_id: int):
    """{department_id: [(membership, [responses])]} for members who have answered. One query."""
    rows = (
        db.query(models.Membership, models.Response)
        .join(models.Response, models.Response.membership_id == models.Membership.id)
        .filter(models.Membership.org_id == org_id)
        .all()
    )
    by_member = defaultdict(list)
    members = {}
    for m, r in rows:
        by_member[m.id].append(r)
        members[m.id] = m
    out = defaultdict(list)
    for mid, responses in by_member.items():
        out[members[mid].department_id].append((members[mid], responses))
    return out


def summarise(people):
    """Group summary for a list of (membership, responses). Never contains anything per-person."""
    averages = [a for a in (person_average(rs) for _, rs in people) if a is not None]
    avg = mean(averages) if averages else None
    return {
        "respondents": len(people),
        "average_score": round(avg, 2) if avg is not None else None,
        "level": maturity_level(avg),
    }


def risk_counts(people):
    """How many *people* have each risk flag (not how many answers), most common first."""
    counts = defaultdict(int)
    for _, rs in people:
        for flag in {f for r in rs for f in (r.flags or [])}:
            counts[flag] += 1
    return [{"risk": k, "people": v} for k, v in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]


def ai_scoring_health(people):
    """How many open answers the AI could and couldn't score. Lets leadership see if the AI is coping."""
    statuses = [r.ai_status for _, rs in people for r in rs if r.ai_status]
    return {"open_answers": len(statuses), "needs_review": statuses.count("needs_review")}
