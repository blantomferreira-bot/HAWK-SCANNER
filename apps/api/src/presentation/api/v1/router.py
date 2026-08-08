from fastapi import APIRouter

from src.presentation.api.v1 import admin, auth, market, user_data

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(market.router)
api_router.include_router(user_data.router)
api_router.include_router(admin.router)
