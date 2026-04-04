from fastapi import APIRouter

from backend.app.api.admin_routes import files_router, router as admin_router, secure_router
from backend.app.api.auth_routes import router as auth_router
from backend.app.api.booking_routes import router as booking_router
from backend.app.api.contact_routes import router as contact_router
from backend.app.api.customer_routes import router as customer_router
from backend.app.api.flight_routes import router as flight_router
from backend.app.api.price_override_routes import router as price_override_router
from backend.app.api.pricing_config_routes import router as pricing_config_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(customer_router)
api_router.include_router(booking_router)
api_router.include_router(admin_router)
api_router.include_router(pricing_config_router)
api_router.include_router(price_override_router)
api_router.include_router(files_router)
api_router.include_router(secure_router)
api_router.include_router(contact_router)
api_router.include_router(flight_router)
