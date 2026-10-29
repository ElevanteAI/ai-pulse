from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models
from ..audit import record
from ..auth import current_membership
from ..db import get_db
from ..services.playbooks import executive_card

router = APIRouter(prefix="/playbooks", tags=["playbooks"])


@router.get("/{risk}")
def get_playbook(risk: str, m: models.Membership = Depends(current_membership), db: Session = Depends(get_db)):
    if m.role != "admin":
        raise HTTPException(403, "Admins only")
    card = executive_card(risk)
    if card is None:
        raise HTTPException(404, "No playbook for this risk")
    record(db, m, "playbook_view", risk)
    db.commit()
    return card
