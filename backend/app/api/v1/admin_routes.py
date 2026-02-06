from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.deps import require_admin
from app.db.deps import get_db
from app.schemas.flight import FlightOut, AdminFlightUpdate
from app.crud.flight import (
    list_flights,
    get_flight_by_id,
    admin_update_flight,
)

router = APIRouter(prefix="/admin", tags=["admin"])


# Admin identity check (keep)
@router.get("/me")
def admin_me(admin=Depends(require_admin)):
    return {
        "id": str(admin.id),
        "email": admin.email,
        "name": admin.name,
        "role": admin.role,
        "is_active": admin.is_active,
    }


# List all imported flights (admin view)
@router.get("/flights", response_model=list[FlightOut])
def admin_list_flights(
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    return list_flights(db)


# Update admin-controlled fields only
@router.patch("/flights/{flight_id}", response_model=FlightOut)
def admin_update_flight_route(
    flight_id: str,
    flight_in: AdminFlightUpdate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    flight = get_flight_by_id(db, flight_id)
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")

    return admin_update_flight(db, flight=flight, flight_in=flight_in)
