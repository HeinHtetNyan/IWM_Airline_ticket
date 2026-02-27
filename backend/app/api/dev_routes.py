from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.db.deps import get_db

router = APIRouter()

@router.get("/db-check")
def db_check(db: Session = Depends(get_db)):
    return {"ok": bool(db.execute(text("SELECT 1")).scalar())}
