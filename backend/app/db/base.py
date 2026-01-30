from app.db.deps import get_db

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
