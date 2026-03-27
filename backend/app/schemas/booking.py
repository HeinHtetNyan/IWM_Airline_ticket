from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, Field, constr

from backend.app.schemas.passenger import PassengerOut


class BookingType(str, Enum):
    ONE_WAY = "ONE_WAY"
    ROUND_TRIP = "ROUND_TRIP"


class BookingStatus(str, Enum):
    PROCESSING = "PROCESSING"
    CONFIRMED = "CONFIRMED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    FAILED = "FAILED"


class BookingCreate(BaseModel):
    type: BookingType
    adults: int = Field(..., gt=0, le=9)
    bundle_key: Optional[str] = None
    airline_code: constr(min_length=2, max_length=3)
    flight_number: constr(min_length=1)
    flight_snapshot: Dict[str, Any]


class BookingBaseOut(BaseModel):
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
    passengers: Optional[List[PassengerOut]] = None
    outbound_completed: Optional[bool] = None
    inbound_completed: Optional[bool] = None

    class Config:
        from_attributes = True


class BookingUserOut(BaseModel):
    name: str
    email: str


class BookingOut(BookingBaseOut):
    user: Optional[BookingUserOut] = None


class CustomerBookingOut(BookingBaseOut):
    ticket_url: Optional[str] = None


class BookingStatusUpdate(BaseModel):
    status: BookingStatus


class TicketUpload(BaseModel):
    ticket_file_url: AnyHttpUrl


class PaymentStatusUpdate(BaseModel):
    payment_status: PaymentStatus


class BookingStats(BaseModel):
    total_bookings: int
    processing: int
    confirmed: int
    cancelled: int
    completed: int
    total_revenue_usd: float
    total_revenue_mmk: float


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
