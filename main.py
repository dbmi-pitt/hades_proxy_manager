from fastapi import FastAPI, HTTPException, Depends, Request, Form, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi_jwt_auth import AuthJWT
from fastapi_jwt_auth.exceptions import AuthJWTException
from pydantic import BaseModel
from pam import authenticate
from httpx import AsyncClient
from typing import Dict

from .src.spawner import Spawner

app = FastAPI()

containers: Dict[str | int, Spawner] = {}


class User(BaseModel):
    username: str
    password: str


class Settings(BaseModel):
    authjwt_secret_key: str = "placeholder__HADES_PROXY_MANAGER"
    authjwt_token_location: set = {"cookies"}
    authjwt_cookie_csrf_protect: bool = False


@AuthJWT.load_config  # type: ignore
def get_config():
    return Settings()


@app.exception_handler(AuthJWTException)
def authjwt_exception_handler(request: Request, exc: AuthJWTException):
    return RedirectResponse(url="/auth/login")


@app.post("/auth/token")
def auth(
    username: str = Form(...), password: str = Form(...), Authorize: AuthJWT = Depends()
):
    user = User(username=username, password=password)
    if authenticate(user.username, user.password) is False:
        raise HTTPException(status_code=401, detail="Bad username or password")

    access_token = Authorize.create_access_token(subject=user.username)
    refresh_token = Authorize.create_refresh_token(subject=user.username)
    Authorize.set_access_cookies(access_token)
    Authorize.set_refresh_cookies(refresh_token)
    return RedirectResponse(url="/")


@app.post("/auth/refresh")
def refresh(Authorize: AuthJWT = Depends()):
    Authorize.jwt_refresh_token_required()
    user = Authorize.get_jwt_subject()
    if user is None:
        raise HTTPException(status_code=401, detail="Identity not found")
    new_access_token = Authorize.create_access_token(subject=user)
    Authorize.set_access_cookies(new_access_token)
    return Response(status_code=200)


@app.delete("/auth/logout")
def logout(Authorize: AuthJWT = Depends()):
    Authorize.jwt_required()
    Authorize.unset_jwt_cookies()
    return RedirectResponse(url="/")


@app.get("/auth/login")
def login_form():
    html_content = """
    <html>
        <head>
            <title>Login</title>
        </head>
        <body>
            <form action="/auth/token" method="post">
                <input type="text" name="username" placeholder="Username" required>
                <input type="password" name="password" placeholder="Password" required>
                <button type="submit">Login</button>
            </form>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/proxy/{path:path}")
async def proxy_get(path: str, response: Response, Authorize: AuthJWT = Depends()):
    Authorize.jwt_required()
    user = Authorize.get_jwt_subject()
    if user is None:
        raise HTTPException(status_code=401, detail="Identity not found")

    if user not in containers:
        containers[user] = Spawner(user)

    host = containers[user].get_internal_ip()
    url = f"http://{host}/{path}"
    async with AsyncClient() as client:
        proxy = await client.get(url)

    response.body = proxy.content
    response.status_code = proxy.status_code
    return response


@app.post("/proxy/{path:path}")
async def proxy_post(
    path: str, request: Request, response: Response, Authorize: AuthJWT = Depends()
):
    Authorize.jwt_required()
    user = Authorize.get_jwt_subject()
    if user is None:
        raise HTTPException(status_code=401, detail="Identity not found")

    if user not in containers:
        containers[user] = Spawner(user)

    host = containers[user].get_internal_ip()
    url = f"http://{host}/{path}"
    async with AsyncClient() as client:
        proxy = await client.post(url, data=await request.body())  # type: ignore

    response.body = proxy.content
    response.status_code = proxy.status_code
    return response


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=7007, log_level="info", reload=True)
