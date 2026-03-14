from fastapi import APIRouter

from app.routes.auth import router as auth_router
from app.routes.businesses import router as businesses_router
from app.routes.competitors import router as competitors_router
from app.routes.dashboard import router as dashboard_router
from app.routes.reviews import router as reviews_router

api_router = APIRouter(prefix="/api")
api_router.include_router(auth_router)
api_router.include_router(businesses_router)
api_router.include_router(competitors_router)
api_router.include_router(reviews_router)
api_router.include_router(dashboard_router)
