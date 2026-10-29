from . import models


def record(db, m: models.Membership, action: str, detail: str | None = None):
    """Add an audit row; the caller's own commit saves it."""
    db.add(models.AuditLog(user_id=m.user_id, org_id=m.org_id, action=action, detail=detail))
