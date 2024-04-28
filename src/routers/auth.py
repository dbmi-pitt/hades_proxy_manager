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
    # ChatGPT generated HTML login form
    return HTMLResponse(
        f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Login</title>
            <style>
                * {{
                    box-sizing: border-box;  /* Ensures padding and borders are included in width/height */
                }}
                body {{
                    font-family: Arial, sans-serif;
                    background-color: #f4f4f9;
                    margin: 0;
                    padding: 0;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                }}
                form {{
                    background: white;
                    padding: 2em;
                    border-radius: 10px;
                    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                    width: 300px;
                }}
                label {{
                    margin-bottom: 0.5em;
                    color: #333;
                    display: block;
                }}
                input[type="text"], input[type="password"] {{
                    width: 100%;
                    padding: 0.8em;
                    margin-bottom: 1em;
                    border-radius: 5px;
                    border: 1px solid #ccc;
                }}
                button {{
                    width: 100%;
                    padding: 1em;
                    border: none;
                    background-color: #5c67f2;
                    color: white;
                    border-radius: 5px;
                    cursor: pointer;
                }}
                button:hover {{
                    background-color: #5058e2;
                }}
            </style>
        </head>
        <body>
            <form action="{router.url_path_for("token")}" method="post">
                <label for="username">Username:</label>
                <input type="text" id="username" name="username" required>
                <label for="password">Password:</label>
                <input type="password" id="password" name="password" required>
                <button type="submit">Login</button>
            </form>
        </body>
        </html>
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
