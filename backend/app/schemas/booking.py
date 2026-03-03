from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field

from app.schemas.passenger import PassengerOut


# CUSTOMER BOOKING

class BookingTypeEnum(str, Enum):
    ONE_WAY = "ONE_WAY"
    ROUND_TRIP = "ROUND_TRIP"


class BookingCreate(BaseModel):
    type: BookingTypeEnum

    adults: int = Field(..., gt=0, le=9)

    bundle_key: Optional[str] = None
    flight_snapshot: Dict[str, Any]


class BookingOut(BaseModel):
    booking_id: UUID
    booking_code: Optional[str]

    type: str
    adults: int

    bundle_key: Optional[str]
    flight_snapshot: Dict[str, Any]

    final_price_usd: float
    final_price_mmk: float

    status: str
    payment_status: str

    created_at: Optional[datetime] = None

    # Passengers
    passengers: Optional[List[PassengerOut]] = None

    # Admin lifecycle tracking
    outbound_completed: Optional[bool] = None
    inbound_completed: Optional[bool] = None

    class Config:
        from_attributes = True


# ADMIN BOOKING ACTIONS

class BookingStatusUpdate(BaseModel):
    status: str


class TicketUpload(BaseModel):
    ticket_file_url: str


class PaymentStatusUpdate(BaseModel):
    payment_status: str


class BookingStats(BaseModel):
    total_bookings: int
    processing: int
    confirmed: int
    cancelled: int
    completed: int
    total_revenue_usd: float
    total_revenue_mmk: float


# ADMIN DASHBOARD

class DashboardFinancial(BaseModel):
    total_paid_bookings: int
    total_revenue_usd: float
    total_revenue_mmk: float


class DashboardOperational(BaseModel):
    processing: int
    paid_processing: int
    confirmed: int
    completed: int
    cancelled: int


class DashboardToday(BaseModel):
    bookings_today: int
    revenue_today_usd: float
    revenue_today_mmk: float


class AdminDashboard(BaseModel):
    financial: DashboardFinancial
    operational: DashboardOperational
    today: DashboardToday


# AUDIT STRUCTURE (SUPER ADMIN ONLY)

class AuditAdminInfo(BaseModel):
    id: Optional[UUID]
    email: Optional[str]
    name: Optional[str]


class AuditPayment(BaseModel):
    status: str
    marked_at: Optional[datetime]
    marked_by: AuditAdminInfo


class AuditStatus(BaseModel):
    current_status: str
    updated_at: Optional[datetime]
    updated_by: AuditAdminInfo


class AuditTicket(BaseModel):
    uploaded_at: Optional[datetime]
    uploaded_by: AuditAdminInfo


class BookingAuditOut(BaseModel):
    payment: AuditPayment
    status: AuditStatus
    ticket: AuditTicket
