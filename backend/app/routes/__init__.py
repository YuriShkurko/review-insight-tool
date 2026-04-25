from fastapi import APIRouter

from app.routes.agent import router as agent_router
from app.routes.auth import router as auth_router
from app.routes.businesses import router as businesses_router
from app.routes.competitors import router as competitors_router
from app.routes.dashboard import router as dashboard_router
from app.routes.debug_ui import router as debug_ui_router
from app.routes.reviews import router as reviews_router
from app.routes.sandbox import router as sandbox_router

api_router = APIRouter(prefix="/api")


@api_router.get("/health", include_in_schema=False)
def health():
    return {"status": "ok"}


api_router.include_router(auth_router)
api_router.include_router(businesses_router)
api_router.include_router(competitors_router)
api_router.include_router(reviews_router)
api_router.include_router(dashboard_router)
api_router.include_router(sandbox_router)
api_router.include_router(debug_ui_router)
api_router.include_router(agent_router)
