from fastapi import APIRouter
from app.health.routes import router as health_router
from app.api.auth_routes import router as auth_router
from app.api.booking_routes import router as booking_router 
from app.api.admin_routes import router as admin_router
from app.api.contact_routes import router as contact_router


api_router = APIRouter(prefix="/api")

api_router.include_router(health_router, tags=["health"])
api_router.include_router(auth_router)
api_router.include_router(booking_router)  
api_router.include_router(admin_router)
api_router.include_router(contact_router)