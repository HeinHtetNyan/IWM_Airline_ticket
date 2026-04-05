import os
import mimetypes
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import func
from uuid import UUID, uuid4
import json
from typing import Optional
from datetime import datetime
from zoneinfo import ZoneInfo

from backend.app.auth.deps import (
    _decode_or_401,
    optional_security,
    require_admin,
    require_super_admin,
)
from backend.app.db.deps import get_db
from backend.app.models.booking import Booking
from backend.app.models.admin_user import AdminUser
from backend.app.models.customer_user import CustomerUser
from backend.app.schemas.common import ExchangeRateUpdate

from backend.app.schemas.booking import (
    BookingStatusUpdate,
    BookingOut,
    BookingUserOut,
    PaymentStatusUpdate,
    AdminDashboard,
    DashboardFinancial,
    DashboardOperational,
    DashboardToday,
)

from backend.app.models.exchange_rate import ExchangeRate

from backend.app.services.booking_auto_cancel import auto_cancel_expired_bookings
from backend.app.services.booking_deletion import delete_cancelled_booking_by_admin
from backend.app.services.storage_service import get_storage
from backend.app.core.config import settings
from backend.app.schemas.staff import StaffResponse, StaffUpdate
from backend.app.schemas.customer_user import CustomerUserResponse, CustomerUserUpdate
from backend.app.crud import staff as staff_crud
from backend.app.crud import customer_users as customer_user_crud
import logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])
files_router = APIRouter(prefix="/files", tags=["files"])
secure_router = APIRouter(prefix="/secure", tags=["files"])
VALID_BOOKING_STATUSES = {"PROCESSING", "CONFIRMED", "COMPLETED", "CANCELLED"}
ALLOWED_UPLOAD_TYPES = {"image/jpeg", "image/png", "application/pdf"}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024
FILE_SIGNATURES = {
    "application/pdf": [b"%PDF-"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "image/jpeg": [b"\xff\xd8\xff"],
}


def _safe_load_flight_snapshot(flight_snapshot: str | None) -> dict:
    try:
        return json.loads(flight_snapshot)
    except (json.JSONDecodeError, TypeError):
        return {}


def _serialize_booking_user(user: CustomerUser | None) -> BookingUserOut | None:
    if not user or not user.email or not user.full_name:
        return None
    return BookingUserOut(
        name=user.full_name,
        email=user.email,
    )


def _detect_folder_from_content_type(content_type: str | None, *, is_booking: bool = False) -> str:
    if content_type in {"image/jpeg", "image/png"}:
        return "private/images"
    if content_type == "application/pdf" or is_booking:
        return "private/tickets"
    raise HTTPException(status_code=400, detail="Invalid file type")


def _generate_uuid_filename(original_name: str | None) -> str:
    extension = ""
    if original_name and "." in original_name:
        extension = f".{original_name.rsplit('.', 1)[-1].lower()}"
    return f"{uuid4().hex}{extension}"


async def _validate_upload_file(file: UploadFile) -> None:
    if file.content_type not in ALLOWED_UPLOAD_TYPES:
        raise HTTPException(status_code=400, detail="Invalid file type")

    await file.seek(0)
    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    await file.seek(0)

    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File too large")

    header = await file.read(16)
    await file.seek(0)

    expected_signatures = FILE_SIGNATURES.get(file.content_type or "")
    if not expected_signatures or not any(header.startswith(signature) for signature in expected_signatures):
        raise HTTPException(status_code=400, detail="File content does not match the declared file type")


def _extract_storage_path(file_url: str | None) -> str | None:
    if not file_url:
        return None

    parsed = urlparse(file_url)
    query_path = parse_qs(parsed.query).get("path", [None])[0]
    if query_path:
        return query_path

    s3_base_url = settings.S3_BASE_URL.rstrip("/")
    if s3_base_url and file_url.startswith(f"{s3_base_url}/"):
        return file_url.removeprefix(f"{s3_base_url}/")

    return parsed.path.lstrip("/") or None


def _build_private_ticket_url(booking_id: UUID, path: str) -> str:
    encoded_path = quote(path, safe="/")
    return f"{settings.BASE_URL.rstrip('/')}/api/secure/tickets/{booking_id}?path={encoded_path}"


def _get_request_actor(
    credentials: HTTPAuthorizationCredentials = Depends(optional_security),
    db: Session = Depends(get_db),
) -> CustomerUser | AdminUser:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    payload = _decode_or_401(credentials.credentials)
    subject = payload.get("sub")
    role = payload.get("role")

    if not subject:
        raise HTTPException(status_code=401, detail="Invalid token")

    if role == "CUSTOMER":
        customer = db.query(CustomerUser).filter(CustomerUser.id == subject).first()
        if not customer or not customer.is_active:
            raise HTTPException(status_code=401, detail="User not found or inactive")
        return customer

    if role in {"STAFF", "SUPER_ADMIN"}:
        admin = db.query(AdminUser).filter(AdminUser.id == subject).first()
        if not admin or not admin.is_active:
            raise HTTPException(status_code=401, detail="Admin not found or inactive")
        return admin

    raise HTTPException(status_code=401, detail="Invalid token")


def _get_booking_file_record(db: Session, file_id: UUID) -> Booking:
    booking = db.query(Booking).filter(Booking.id == file_id).first()
    if not booking or not booking.ticket_file_url:
        raise HTTPException(status_code=404, detail="File not found")
    return booking


def _ensure_booking_file_access(booking: Booking, actor: CustomerUser | AdminUser) -> None:
    if isinstance(actor, AdminUser):
        return
    if booking.customer_id != actor.id:
        raise HTTPException(status_code=403, detail="Unauthorized access")

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


# ADMIN BOOKING LIST
@router.get("/bookings", response_model=list[BookingOut])
def list_all_bookings(
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin),
):
    query = (
        db.query(Booking, CustomerUser)
        .outerjoin(CustomerUser, Booking.customer_id == CustomerUser.id)
    )

    if status:
        if status not in VALID_BOOKING_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid booking status")
        query = query.filter(Booking.status == status)

    bookings = query.order_by(Booking.created_at.desc()).offset(offset).limit(limit).all()

    return [
        BookingOut(
            booking_id=booking.id,
            booking_code=booking.booking_code,
            type=booking.type,
            adults=booking.adults,
            bundle_key=booking.bundle_key,
            flight_snapshot=_safe_load_flight_snapshot(booking.flight_snapshot),
            final_price_usd=booking.final_price_usd,
            final_price_mmk=booking.final_price_mmk,
            status=booking.status,
            payment_status=booking.payment_status,
            created_at=booking.created_at,
            passengers=None,
            user=_serialize_booking_user(user),
        )
        for booking, user in bookings
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
    booking_row = (
        db.query(Booking, CustomerUser)
        .outerjoin(CustomerUser, Booking.customer_id == CustomerUser.id)
        .filter(Booking.id == booking_id)
        .first()
    )

    if not booking_row:
        raise HTTPException(status_code=404, detail="Booking not found")
    booking, user = booking_row

    return BookingOut(
        booking_id=booking.id,
        booking_code=booking.booking_code,
        type=booking.type,
        adults=booking.adults,
        bundle_key=booking.bundle_key,
        flight_snapshot=_safe_load_flight_snapshot(booking.flight_snapshot),
        final_price_usd=booking.final_price_usd,
        final_price_mmk=booking.final_price_mmk,
        status=booking.status,
        payment_status=booking.payment_status,
        created_at=booking.created_at,
        passengers=booking.passengers,
        outbound_completed=booking.outbound_completed,
        inbound_completed=booking.inbound_completed,
        user=_serialize_booking_user(user),
    )


@router.delete("/bookings/{booking_id}")
def delete_booking(
    booking_id: UUID,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin),
):
    return delete_cancelled_booking_by_admin(
        db=db,
        booking_id=booking_id,
        admin=admin,
    )


# UPDATE PAYMENT STATUS
@router.put("/bookings/{booking_id}/payment-status")
def update_payment_status(
    booking_id: UUID,
    payload: PaymentStatusUpdate,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin),
):
    booking = (
        db.query(Booking)
        .filter(Booking.id == booking_id)
        .with_for_update()
        .first()
    )

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
    booking = (
        db.query(Booking)
        .filter(Booking.id == booking_id)
        .with_for_update()
        .first()
    )

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
async def upload_ticket(
    booking_id: UUID,
    file: UploadFile = File(...),
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

    await _validate_upload_file(file)

    storage = get_storage()
    folder = _detect_folder_from_content_type(file.content_type, is_booking=True)
    path = f"{folder}/{_generate_uuid_filename(file.filename)}"
    try:
        await storage.save(file, path)
    except Exception as exc:
        logger.exception("Ticket upload failed for booking %s", booking_id)
        raise HTTPException(status_code=500, detail="Storage failure") from exc

    file_url = _build_private_ticket_url(booking.id, path)

    # Files are not stored in the DB as base64/blob content because object
    # storage and filesystem backends scale better, while the DB keeps metadata.
    booking.ticket_file_url = file_url
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
        "file_url": booking.ticket_file_url,
        "file_type": file.content_type,
        "original_name": file.filename,
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
            return {
                "id": str(admin_id),
                "email": None,
                "name": "[deleted]",
            }
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


@files_router.put("/replace/{booking_id}")
async def replace_file(
    booking_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin),
):
    booking = _get_booking_file_record(db, booking_id)

    if booking.status == "CANCELLED":
        raise HTTPException(status_code=400, detail="Cannot replace ticket for cancelled booking")

    if booking.status == "COMPLETED":
        raise HTTPException(status_code=400, detail="Cannot replace ticket for completed booking")

    await _validate_upload_file(file)

    storage = get_storage()
    old_path = _extract_storage_path(booking.ticket_file_url)

    folder = _detect_folder_from_content_type(file.content_type, is_booking=True)
    new_path = f"{folder}/{_generate_uuid_filename(file.filename)}"
    try:
        await storage.save(file, new_path)
    except Exception as exc:
        logger.exception("Ticket replacement upload failed for booking %s", booking_id)
        raise HTTPException(status_code=500, detail="Storage failure") from exc

    booking.ticket_file_url = _build_private_ticket_url(booking.id, new_path)
    booking.ticket_uploaded_at = datetime.now(ZoneInfo("UTC"))
    booking.ticket_uploaded_by_admin_id = admin.id

    db.commit()
    db.refresh(booking)

    # Delete the old file only after the new upload and DB update succeed so a
    # failed replacement never leaves the booking without a ticket.
    if old_path:
        try:
            await storage.delete(old_path)
        except Exception:
            logger.exception("Old ticket cleanup failed for booking %s", booking_id)

    return {
        "file_id": booking.id,
        "file_url": booking.ticket_file_url,
        "file_type": file.content_type,
        "original_name": file.filename,
        "updated_by": admin.email,
    }


@secure_router.get("/tickets/{booking_id}")
async def get_secure_ticket(
    booking_id: UUID,
    actor: CustomerUser | AdminUser = Depends(_get_request_actor),
    db: Session = Depends(get_db),
):
    booking = _get_booking_file_record(db, booking_id)
    _ensure_booking_file_access(booking, actor)

    ticket_path = _extract_storage_path(booking.ticket_file_url)
    if not ticket_path:
        raise HTTPException(status_code=404, detail="File not found")

    storage = get_storage()

    if settings.STORAGE_TYPE.lower() == "s3":
        try:
            signed_url = await storage.generate_presigned_url(ticket_path, expires=300)
        except Exception as exc:
            logger.exception("Signed URL generation failed for booking %s", booking_id)
            raise HTTPException(status_code=500, detail="Storage failure") from exc
        return RedirectResponse(url=signed_url, status_code=307)

    base_dir = Path(settings.UPLOAD_DIR).resolve()
    local_path = (base_dir / ticket_path).resolve()

    if not local_path.is_relative_to(base_dir):
        raise HTTPException(status_code=403, detail="Invalid or unsafe file path")

    if not local_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    # Private ticket files are served through an authenticated endpoint instead
    # of the public static mount so browsers cannot fetch them anonymously.
    guessed_media_type, _ = mimetypes.guess_type(local_path.name)
    return FileResponse(
        path=local_path,
        media_type=guessed_media_type or "application/octet-stream",
        filename=local_path.name,
    )


@files_router.delete("/{booking_id}")
async def delete_file(
    booking_id: UUID,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin),
):
    booking = _get_booking_file_record(db, booking_id)

    if booking.status == "CANCELLED":
        raise HTTPException(status_code=400, detail="Cannot delete ticket for cancelled booking")

    if booking.status == "COMPLETED":
        raise HTTPException(status_code=400, detail="Cannot delete ticket for completed booking")

    storage = get_storage()

    old_path = _extract_storage_path(booking.ticket_file_url)
    if old_path:
        try:
            await storage.delete(old_path)
        except Exception as exc:
            logger.exception("Ticket deletion failed for booking %s", booking_id)
            raise HTTPException(status_code=500, detail="Storage failure") from exc

    booking.ticket_file_url = None
    booking.ticket_uploaded_at = None
    booking.ticket_uploaded_by_admin_id = None

    db.commit()

    return {
        "file_id": booking.id,
        "deleted": True,
        "deleted_by": admin.email,
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
    _: AdminUser = Depends(require_super_admin)
):
    return staff_crud.get_staff_list(db)

#get staff detail
@router.get("/staff/{staff_id}", response_model=StaffResponse)
def get_staff(
    staff_id: UUID,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(require_super_admin)
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
    _: AdminUser = Depends(require_super_admin)
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

    return staff_crud.deactivate_staff(db, staff)


#activate staff
@router.patch("/staff/{staff_id}/activate")
def activate_staff(
    staff_id: UUID,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(require_super_admin)
):
    staff = staff_crud.get_staff(db, staff_id)

    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    return staff_crud.activate_staff(db, staff)


#customer management
#list customers
@router.get("/customers", response_model=list[CustomerUserResponse])
def list_customers(
    db: Session = Depends(get_db),
    _: AdminUser = Depends(require_super_admin)
):
    return customer_user_crud.get_customers(db)


#get customer detail
@router.get("/customers/{customer_id}", response_model=CustomerUserResponse)
def get_customer(
    customer_id: UUID,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(require_super_admin)
):
    customer = customer_user_crud.get_customer(db, customer_id)

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    return customer


#update customer
@router.patch("/customers/{customer_id}", response_model=CustomerUserResponse)
def update_customer(
    customer_id: UUID,
    payload: CustomerUserUpdate,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(require_super_admin)
):
    customer = customer_user_crud.get_customer(db, customer_id)

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    return customer_user_crud.update_customer(db, customer, payload.model_dump(exclude_unset=True))


#deactivate customer
@router.patch("/customers/{customer_id}/deactivate", response_model=CustomerUserResponse)
def deactivate_customer(
    customer_id: UUID,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(require_super_admin)
):
    customer = customer_user_crud.get_customer(db, customer_id)

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    return customer_user_crud.deactivate_customer(db, customer)


#activate customer
@router.patch("/customers/{customer_id}/activate", response_model=CustomerUserResponse)
def activate_customer(
    customer_id: UUID,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(require_super_admin)
):
    customer = customer_user_crud.get_customer(db, customer_id)

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    return customer_user_crud.activate_customer(db, customer)
