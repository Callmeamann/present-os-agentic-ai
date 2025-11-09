from fastapi import APIRouter
from app.api.v1.endpoints import auth, goals, actions

api_router = APIRouter()

# Include all the endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(goals.router, prefix="/goals", tags=["Goals"])
api_router.include_router(actions.router, prefix="/actions", tags=["AI Actions"]) 