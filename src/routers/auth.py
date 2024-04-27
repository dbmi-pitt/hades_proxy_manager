from datetime import timedelta

from docker.errors import DockerException
from fastapi import APIRouter, Form, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi_proxy_lib.core.http import ReverseHttpProxy
from httpx import AsyncClient

from src import instances, settings
from src.core.container import Container
from src.models import Instance, User
from src.routers import main_router
from src.utils.auth import authenticate_user, create_access_token

router = APIRouter(prefix=f"{settings.PREFIX}/_", tags=["auth"])


@router.get("/login", response_class=HTMLResponse)
async def login():
    return HTMLResponse(
        f"""
        <form action="{router.url_path_for("token")}" method="post">
        <label for="username">Username:</label>
        <input type="text" id="username" name="username" required />
        <label for="password">Password:</label>
        <input type="password" id="password" name="password" required />
        <button type="submit">Login</button>
        </form>
        """
    )


@router.post("/token", response_class=RedirectResponse)
async def token(
    response: Response, username: str = Form(...), password: str = Form(...)
):
    if authenticate_user(username, password):
        response = RedirectResponse(main_router.url_path_for("root"), status_code=303)
        access_token_expires = timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
        hpm_access_token = create_access_token(
            data={"sub": username}, expires_delta=access_token_expires
        )
        response.set_cookie(
            key="hpm_access_token",
            value=str(hpm_access_token),
            httponly=True,
        )

        if username not in instances:
            user = User(username=username)
            try:
                container = Container(user)
            except DockerException:
                return response
            target_url = f"http://{container.internal_host}/"
            instances[username] = Instance(
                user=user,
                container=Container(user),
                proxy=ReverseHttpProxy(AsyncClient(), base_url=target_url),
            )

        return response
    else:
        return RedirectResponse(url=router.url_path_for("login"), status_code=303)
