from fastapi import APIRouter
from app.health.routes import router as health_router
from app.api.v1.auth_routes import router as auth_router
from app.api.v1.booking_routes import router as booking_router  # add

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health_router, tags=["health"])
api_router.include_router(auth_router)
api_router.include_router(booking_router)  
