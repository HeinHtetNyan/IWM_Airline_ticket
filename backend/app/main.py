from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.session import engine
from app.models.base import Base
from app.models import admin_user, customer_user 


from app.db.deps import get_db
from app.api.v1.router import api_router

app = FastAPI(title="Air Ticket Booking API")

Base.metadata.create_all(bind=engine)

app.include_router(api_router)

@app.get("/")
def root():
    return {"message": "FastAPI running in Docker 🚀"}
 
@app.get("/db-check")
def db_check(db: Session = Depends(get_db)):
    return {"ok": bool(db.execute(text("SELECT 1")).scalar())}
