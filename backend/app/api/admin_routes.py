from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from uuid import UUID
import json
from typing import Optional
from datetime import datetime

from app.auth.deps import (
    require_admin,
    require_super_admin,
)
from app.db.deps import get_db
from app.models.booking import Booking
from app.models.admin_user import AdminUser

from app.schemas.booking import (
    BookingStatusUpdate,
    BookingOut,
    TicketUpload,
    PaymentStatusUpdate,
    AdminDashboard,
    DashboardFinancial,
    DashboardOperational,
    DashboardToday,
)

from app.schemas.flight_override import (
    FlightOverrideCreate,
    FlightOverrideResponse,
    FlightOverrideUpdate
)

from app.crud.flight_override import (
    create_override,
    get_all_overrides,
    update_override_price,
    delete_override
)

from app.services.booking_auto_cancel import auto_cancel_expired_bookings

router = APIRouter(prefix="/admin", tags=["admin"])


# ADMIN IDENTITY
@router.get("/me")
def admin_me(admin: AdminUser = Depends(require_admin)):
    return {
        "id": str(admin.id),
        "email": admin.email,
        "name": admin.name,
        "role": admin.role,
        "is_active": admin.is_active,
    }


# DASHBOARD
@router.get("/dashboard", response_model=AdminDashboard)
def admin_dashboard(
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin),
):
    today_start = datetime.utcnow().replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    total_paid_bookings = db.query(func.count(Booking.id)).filter(
        Booking.payment_status == "PAID"
    ).scalar()

    revenue_totals = db.query(
        func.coalesce(func.sum(Booking.final_price_usd), 0),
        func.coalesce(func.sum(Booking.final_price_mmk), 0),
    ).filter(
        Booking.payment_status == "PAID"
    ).first()

    processing = db.query(func.count(Booking.id)).filter(
        Booking.status == "PROCESSING"
    ).scalar()

    paid_processing = db.query(func.count(Booking.id)).filter(
        Booking.status == "PROCESSING",
        Booking.payment_status == "PAID"
    ).scalar()

    confirmed = db.query(func.count(Booking.id)).filter(
        Booking.status == "CONFIRMED"
    ).scalar()

    completed = db.query(func.count(Booking.id)).filter(
        Booking.status == "COMPLETED"
    ).scalar()

    cancelled = db.query(func.count(Booking.id)).filter(
        Booking.status == "CANCELLED"
    ).scalar()

    bookings_today = db.query(func.count(Booking.id)).filter(
        Booking.created_at >= today_start
    ).scalar()

    revenue_today = db.query(
        func.coalesce(func.sum(Booking.final_price_usd), 0),
        func.coalesce(func.sum(Booking.final_price_mmk), 0),
    ).filter(
        Booking.payment_status == "PAID",
        Booking.created_at >= today_start
    ).first()

    return AdminDashboard(
        financial=DashboardFinancial(
            total_paid_bookings=total_paid_bookings,
            total_revenue_usd=revenue_totals[0],
            total_revenue_mmk=revenue_totals[1],
        ),
        operational=DashboardOperational(
            processing=processing,
            paid_processing=paid_processing,
            confirmed=confirmed,
            completed=completed,
            cancelled=cancelled,
        ),
        today=DashboardToday(
            bookings_today=bookings_today,
            revenue_today_usd=revenue_today[0],
            revenue_today_mmk=revenue_today[1],
        ),
    )


# FLIGHT OVERRIDES (SUPER ADMIN ONLY)
@router.post("/overrides", response_model=FlightOverrideResponse)
def create_flight_override(
    override: FlightOverrideCreate,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_super_admin),
):
    return create_override(db, override)


@router.get("/overrides", response_model=list[FlightOverrideResponse])
def list_flight_overrides(
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_super_admin),
):
    return get_all_overrides(db)


@router.put("/overrides/{override_id}", response_model=FlightOverrideResponse)
def update_flight_override(
    override_id: str,
    payload: FlightOverrideUpdate,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_super_admin),
):
    return update_override_price(db, override_id, payload.override_price_usd)


@router.delete("/overrides/{override_id}")
def delete_flight_override(
    override_id: str,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_super_admin),
):
    delete_override(db, override_id)
    return {"message": "Override deleted successfully"}


# ADMIN BOOKING LIST
@router.get("/bookings", response_model=list[BookingOut])
def list_all_bookings(
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin),
):
    query = db.query(Booking)

    if status:
        query = query.filter(Booking.status == status)

    bookings = query.order_by(Booking.created_at.desc()).all()

    return [
        BookingOut(
            booking_id=b.id,
            booking_code=b.booking_code,
            type=b.type,
            adults=b.adults,
            bundle_key=b.bundle_key,
            flight_snapshot=json.loads(b.flight_snapshot),
            final_price_usd=b.final_price_usd,
            final_price_mmk=b.final_price_mmk,
            status=b.status,
            payment_status=b.payment_status,
            created_at=b.created_at,
            passengers=None,
        )
        for b in bookings
    ]


# ADMIN BOOKING DETAIL
@router.get("/bookings/{booking_id}", response_model=BookingOut)
def get_booking_detail(
    booking_id: UUID,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin),
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    return BookingOut(
        booking_id=booking.id,
        booking_code=booking.booking_code,
        type=booking.type,
        adults=booking.adults,
        bundle_key=booking.bundle_key,
        flight_snapshot=json.loads(booking.flight_snapshot),
        final_price_usd=booking.final_price_usd,
        final_price_mmk=booking.final_price_mmk,
        status=booking.status,
        payment_status=booking.payment_status,
        created_at=booking.created_at,
        passengers=booking.passengers,
    )


# UPDATE PAYMENT STATUS
@router.put("/bookings/{booking_id}/payment-status")
def update_payment_status(
    booking_id: UUID,
    payload: PaymentStatusUpdate,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin),
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    allowed = {"PENDING", "PAID", "FAILED"}
    if payload.payment_status not in allowed:
        raise HTTPException(status_code=400, detail="Invalid payment status")

    if booking.status == "CANCELLED":
        raise HTTPException(
            status_code=400,
            detail="Cannot change payment for cancelled booking"
        )

    booking.payment_status = payload.payment_status
    booking.payment_marked_at = datetime.utcnow()
    booking.payment_marked_by_admin_id = admin.id

    if payload.payment_status == "FAILED":
        booking.status = "CANCELLED"
        booking.status_updated_at = datetime.utcnow()
        booking.status_updated_by_admin_id = admin.id

    db.commit()
    db.refresh(booking)

    return {
        "booking_id": booking.id,
        "payment_status": booking.payment_status,
        "updated_by": admin.email,
    }


# UPDATE BOOKING STATUS
@router.put("/bookings/{booking_id}")
def update_booking_status(
    booking_id: UUID,
    payload: BookingStatusUpdate,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin),
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if payload.status == "COMPLETED":
        raise HTTPException(
            status_code=400,
            detail="COMPLETED status is system controlled only"
        )

    booking.status = payload.status
    booking.status_updated_at = datetime.utcnow()
    booking.status_updated_by_admin_id = admin.id

    db.commit()
    db.refresh(booking)

    return {
        "booking_id": booking.id,
        "new_status": booking.status,
        "updated_by": admin.email,
    }


# UPLOAD TICKET
@router.put("/bookings/{booking_id}/upload-ticket")
def upload_ticket(
    booking_id: UUID,
    payload: TicketUpload,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin),
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.payment_status != "PAID":
        raise HTTPException(
            status_code=400,
            detail="Cannot upload ticket before payment is PAID"
        )

    if booking.ticket_file_url is not None:
        raise HTTPException(
            status_code=400,
            detail="Ticket already uploaded"
        )

    booking.ticket_file_url = payload.ticket_file_url
    booking.ticket_uploaded_at = datetime.utcnow()
    booking.ticket_uploaded_by_admin_id = admin.id

    booking.status = "CONFIRMED"
    booking.status_updated_at = datetime.utcnow()
    booking.status_updated_by_admin_id = admin.id

    db.commit()
    db.refresh(booking)

    return {
        "booking_id": booking.id,
        "ticket_file_url": booking.ticket_file_url,
        "ticket_uploaded_at": booking.ticket_uploaded_at,
        "status": booking.status,
        "uploaded_by": admin.email,
    }


# AUTO CANCEL
@router.post("/bookings/auto-cancel")
def trigger_auto_cancel(
    expire_minutes: int = 30,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin),
):
    return auto_cancel_expired_bookings(db, expire_minutes)


# BOOKING AUDIT (SUPER ADMIN ONLY)
@router.get("/bookings/{booking_id}/audit")
def get_booking_audit(
    booking_id: UUID,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_super_admin),
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    def get_admin_info(admin_id):
        if not admin_id:
            return None
        admin = db.query(AdminUser).filter(
            AdminUser.id == admin_id
        ).first()
        if not admin:
            return None
        return {
            "id": str(admin.id),
            "email": admin.email,
            "name": admin.name,
        }

    return {
        "payment": {
            "status": booking.payment_status,
            "marked_at": booking.payment_marked_at,
            "marked_by": get_admin_info(booking.payment_marked_by_admin_id),
        },
        "status": {
            "current_status": booking.status,
            "updated_at": booking.status_updated_at,
            "updated_by": get_admin_info(booking.status_updated_by_admin_id),
        },
        "ticket": {
            "uploaded_at": booking.ticket_uploaded_at,
            "uploaded_by": get_admin_info(booking.ticket_uploaded_by_admin_id),
        },
    }
