import bcrypt
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session

from .config import SECRET_KEY, TOKEN_HOURS
from .db import get_db
from . import models


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False


def make_token(user_id: int, org_id: int | None = None) -> str:
    payload = {
        "sub": str(user_id),
        "org": org_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def _decode(authorization: str | None):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing token")
    try:
        data = jwt.decode(authorization[7:], SECRET_KEY, algorithms=["HS256"], options={"require": ["sub", "exp"]})
        if not isinstance(data["sub"], str) or not data["sub"].isdigit() or int(data["sub"]) < 1:
            raise jwt.InvalidTokenError("Invalid user ID")
        if data.get("org") is not None and (type(data["org"]) is not int or data["org"] < 1):
            raise jwt.InvalidTokenError("Invalid organization ID")
        return data
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid token")


def current_user(authorization: str | None = Header(None), db: Session = Depends(get_db)) -> models.User:
    data = _decode(authorization)
    user = db.get(models.User, int(data["sub"]))
    if not user:
        raise HTTPException(401, "Unknown user")
    return user


def current_membership(authorization: str | None = Header(None), db: Session = Depends(get_db)) -> models.Membership:
    data = _decode(authorization)
    if not data.get("org"):
        raise HTTPException(400, "Select an organization first")
    m = (
        db.query(models.Membership)
        .filter_by(user_id=int(data["sub"]), org_id=data["org"])
        .first()
    )
    if not m:
        raise HTTPException(403, "Not a member of this organization")
    return m
