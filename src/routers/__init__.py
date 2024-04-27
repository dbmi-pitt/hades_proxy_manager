from fastapi import APIRouter

from src import settings

main_router = APIRouter(prefix=f"{settings.PREFIX}", tags=["main"])

from src.routers.auth import router as auth_router
from src.routers.proxy import router as proxy_router
