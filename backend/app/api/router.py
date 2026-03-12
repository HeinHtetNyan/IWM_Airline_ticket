from fastapi import APIRouter

from backend.app.api.admin_routes import router as admin_router
from backend.app.api.auth_routes import router as auth_router
from backend.app.api.booking_routes import router as booking_router
from backend.app.api.contact_routes import router as contact_router
from backend.app.api.flight_routes import router as flight_router
from backend.app.health.routes import router as health_router

api_router = APIRouter()

api_router.include_router(health_router, tags=["health"])
api_router.include_router(auth_router)
api_router.include_router(booking_router)
api_router.include_router(admin_router)
api_router.include_router(contact_router)
api_router.include_router(flight_router)
