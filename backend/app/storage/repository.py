from sqlalchemy import select
from ..utils.errors import AppError

def require(session, model, identity: str):
    row = session.get(model, str(identity))
    if row is None:
        raise AppError("not_found", "The requested resource does not exist.", 404)
    return row

def recent(session, model, limit=100, offset=0):
    return list(session.scalars(select(model).order_by(model.created_at.desc()).offset(offset).limit(limit)))
