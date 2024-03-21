from contextlib import asynccontextmanager
from typing import AsyncIterator

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from starlette.requests import Request

from src import instances, settings
from src.routers import auth_router, proxy_router
from src.utils.auth import get_current_user


@asynccontextmanager
async def close_proxy_event(_: FastAPI) -> AsyncIterator[None]:
    yield
    for instance in instances.values():
        await instance.proxy.aclose()


app = FastAPI(lifespan=close_proxy_event)


@app.get("/")
async def root(request: Request):
    try:
        username = await get_current_user(request)
    except HTTPException:
        return RedirectResponse(url="/_/login", status_code=303)
    return RedirectResponse(f"/{username}")


app.include_router(auth_router)
app.include_router(proxy_router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=True)
