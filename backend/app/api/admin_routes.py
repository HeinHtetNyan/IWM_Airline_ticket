from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from uuid import UUID
import json
from typing import Optional
from datetime import datetime
from zoneinfo import ZoneInfo

from backend.app.auth.deps import (
    require_admin,
    require_super_admin,
)
from backend.app.db.deps import get_db
from backend.app.models.booking import Booking
from backend.app.models.admin_user import AdminUser
from backend.app.schemas.common import ExchangeRateUpdate

from backend.app.schemas.booking import (
    BookingStatusUpdate,
    BookingOut,
    TicketUpload,
    PaymentStatusUpdate,
    AdminDashboard,
    DashboardFinancial,
    DashboardOperational,
    DashboardToday,
)

from backend.app.schemas.flight_override import (
    FlightOverrideCreate,
    FlightOverrideResponse,
    FlightOverrideUpdate
)

from backend.app.crud.flight_override import (
    create_override,
    get_all_overrides,
    update_override_price,
    delete_override
)

from backend.app.models.exchange_rate import ExchangeRate

from backend.app.services.booking_auto_cancel import auto_cancel_expired_bookings
from backend.app.schemas.staff import StaffResponse, StaffUpdate
from backend.app.crud import staff as staff_crud
import logging
logger = logging.getLogger(__name__)

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
    request: Request,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin),
):
    tz_name = request.headers.get("X-Timezone", "UTC")
    try:
        local_tz = ZoneInfo(tz_name)
    except Exception:
        logger.warning(f"Invalid timezone received: {tz_name}")
        local_tz = ZoneInfo("UTC")

    today_start = datetime.now(local_tz).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(ZoneInfo("UTC"))

    total_paid_bookings, revenue_usd, revenue_mmk = db.query(
        func.count(Booking.id),
        func.coalesce(func.sum(Booking.final_price_usd), 0),
        func.coalesce(func.sum(Booking.final_price_mmk), 0),
    ).filter(
        Booking.payment_status == "PAID",
        Booking.status != "CANCELLED"
    ).one()

    status_counts = dict(
        db.query(Booking.status, func.count(Booking.id))
        .group_by(Booking.status)
        .all()
    )

    paid_processing = db.query(func.count(Booking.id)).filter(
        Booking.status == "PROCESSING",
        Booking.payment_status == "PAID",
        Booking.status != "CANCELLED"
    ).scalar()

    bookings_today = db.query(func.count(Booking.id)).filter(
        Booking.created_at >= today_start
    ).scalar()

    revenue_today = db.query(
        func.coalesce(func.sum(Booking.final_price_usd), 0),
        func.coalesce(func.sum(Booking.final_price_mmk), 0),
    ).filter(
        Booking.payment_status == "PAID",
        Booking.status != "CANCELLED",
        Booking.created_at >= today_start
    ).one()

    return AdminDashboard(
        financial=DashboardFinancial(
            total_paid_bookings=total_paid_bookings,
            total_revenue_usd=revenue_usd,
            total_revenue_mmk=revenue_mmk,
        ),
        operational=DashboardOperational(
            processing=status_counts.get("PROCESSING", 0),
            paid_processing=paid_processing,
            confirmed=status_counts.get("CONFIRMED", 0),
            completed=status_counts.get("COMPLETED", 0),
            cancelled=status_counts.get("CANCELLED", 0),
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
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin),
):
    query = db.query(Booking)

    if status:
        query = query.filter(Booking.status == status)

    bookings = query.order_by(Booking.created_at.desc()).offset(offset).limit(limit).all()

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


# AUTO CANCEL
@router.post("/bookings/auto-cancel")
def trigger_auto_cancel(
    expire_minutes: int = 30,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin),
):
    return auto_cancel_expired_bookings(db, expire_minutes)


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
        outbound_completed=booking.outbound_completed,
        inbound_completed=booking.inbound_completed,
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

    if booking.status == "COMPLETED":
        raise HTTPException(
            status_code=400,
            detail="Cannot change payment for completed booking"
        )

    booking.payment_status = payload.payment_status
    booking.payment_marked_at = datetime.now(ZoneInfo("UTC"))
    booking.payment_marked_by_admin_id = admin.id

    if payload.payment_status == "FAILED":
        booking.status = "CANCELLED"
        booking.status_updated_at = datetime.now(ZoneInfo("UTC"))
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

    if booking.status == "COMPLETED":
        raise HTTPException(status_code=400, detail="Cannot change status for completed booking")

    if payload.status == booking.status:
        return {
            "booking_id": booking.id,
            "new_status": booking.status,
            "updated_by": admin.email,
        }

    allowed_transitions = {
        "PROCESSING": {"PROCESSING", "CONFIRMED", "CANCELLED"},
        "CONFIRMED": {"CONFIRMED", "COMPLETED", "CANCELLED"},
        "COMPLETED": {"COMPLETED"},
        "CANCELLED": {"CANCELLED"},
    }

    if payload.status not in allowed_transitions.get(booking.status, set()):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot change booking status from {booking.status} to {payload.status}",
        )

    if payload.status == "COMPLETED" and booking.payment_status != "PAID":
        raise HTTPException(status_code=400, detail="Cannot complete booking before payment is PAID")

    booking.status = payload.status
    if booking.type == "ROUND_TRIP" and payload.status == "COMPLETED":
        booking.outbound_completed = True
        booking.inbound_completed = True
    booking.status_updated_at = datetime.now(ZoneInfo("UTC"))
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

    if booking.status == "CANCELLED":
        raise HTTPException(status_code=400, detail="Cannot upload ticket for cancelled booking")

    if booking.status == "COMPLETED":
        raise HTTPException(status_code=400, detail="Cannot upload ticket for completed booking")

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

    booking.ticket_file_url = str(payload.ticket_file_url)
    booking.ticket_uploaded_at = datetime.now(ZoneInfo("UTC"))
    booking.ticket_uploaded_by_admin_id = admin.id

    if booking.status != "CONFIRMED":
        booking.status = "CONFIRMED"
        booking.status_updated_at = datetime.now(ZoneInfo("UTC"))
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
        admin_obj = db.get(AdminUser, admin_id)
        if not admin_obj:
            raise HTTPException(status_code=404, detail=f"Admin {admin_id} referenced in audit was not found")
        admin = admin_obj
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
# EXCHANGE RATE (ADMIN CONFIG)
@router.get("/exchange-rate")
def get_exchange_rate(
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin),
):
    rate = db.query(ExchangeRate).filter(ExchangeRate.id == 1).first()

    if not rate:
        raise HTTPException(
            status_code=404,
            detail="Exchange rate not configured"
        )

    return {
        "usd_to_mmk": rate.usd_to_mmk,
        "created_at": rate.created_at,
    }


@router.put("/exchange-rate")
def update_exchange_rate(
    payload: ExchangeRateUpdate,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_super_admin),
):
    rate = db.query(ExchangeRate).filter(ExchangeRate.id == 1).first()

    if not rate:
        rate = ExchangeRate(id=1, usd_to_mmk=payload.usd_to_mmk)
        db.add(rate)
    else:
        rate.usd_to_mmk = payload.usd_to_mmk

    db.commit()
    db.refresh(rate)

    return {
        "message": "Exchange rate updated successfully",
        "usd_to_mmk": rate.usd_to_mmk,
    }


#staff management
#list staff
@router.get("/staff", response_model=list[StaffResponse])
def list_staff(
    db: Session = Depends(get_db),
    _: str = Depends(require_super_admin)
):
    return staff_crud.get_staff_list(db)

#get staff detail
@router.get("/staff/{staff_id}", response_model=StaffResponse)
def get_staff(
    staff_id: UUID,
    db: Session = Depends(get_db),
    _: str = Depends(require_super_admin)
):
    staff = staff_crud.get_staff(db, staff_id)

    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    return staff

#update staff
@router.patch("/staff/{staff_id}", response_model=StaffResponse)
def update_staff(
    staff_id: UUID,
    payload: StaffUpdate,
    db: Session = Depends(get_db),
    _: str = Depends(require_super_admin)
):
    staff = staff_crud.get_staff(db, staff_id)

    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    return staff_crud.update_staff(db, staff, payload.model_dump(exclude_unset=True))


#deactivate staff
@router.patch("/staff/{staff_id}/deactivate")
def deactivate_staff(
    staff_id: UUID,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(require_super_admin),
):
    staff = staff_crud.get_staff(db, staff_id)

    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    # Prevent disabling yourself
    if staff.id == current_admin.id:
        raise HTTPException(
            status_code=400,
            detail="You cannot deactivate your own account"
        )

    # Prevent removing last SUPER_ADMIN
    if staff.role == "SUPER_ADMIN":
        total_super_admins = staff_crud.count_super_admins(db)

        if total_super_admins <= 1:
            raise HTTPException(
                status_code=400,
                detail="Cannot deactivate the last SUPER_ADMIN"
            )

    return staff_crud.deactivate_staff(db, staff)


#activate staff
@router.patch("/staff/{staff_id}/activate")
def activate_staff(
    staff_id: UUID,
    db: Session = Depends(get_db),
    _: str = Depends(require_super_admin),
):
    staff = staff_crud.get_staff(db, staff_id)

    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    return staff_crud.activate_staff(db, staff)


#delete staff
@router.delete("/staff/{staff_id}")
def delete_staff(
    staff_id: UUID,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(require_super_admin),
):
    staff = staff_crud.get_staff(db, staff_id)

    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    if staff.id == current_admin.id:
        raise HTTPException(
            status_code=400,
            detail="You cannot delete your own account"
        )

    if staff.role == "SUPER_ADMIN":
        total_super_admins = staff_crud.count_super_admins(db)

        if total_super_admins <= 1:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete the last SUPER_ADMIN"
            )

    staff_crud.delete_staff(db, staff)

    return {"message": "Staff deleted"}