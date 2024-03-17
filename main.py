from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict

from fastapi import FastAPI, HTTPException, Response, Request, Form
from fastapi_proxy_lib.core.http import ReverseHttpProxy
from fastapi.responses import HTMLResponse, RedirectResponse
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Dict, Optional
from src.spawner import Spawner
from httpx import AsyncClient
import pam
from starlette.requests import Request

from src.spawner import Spawner

SECRET_KEY = "placeholder__HADES_PROXY_MANAGER"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

proxies: Dict[str, ReverseHttpProxy] = {}
containers: Dict[str, Spawner] = {}


@asynccontextmanager
async def close_proxy_event(_: FastAPI) -> AsyncIterator[None]:
    yield
    for proxy in proxies.values():
        await proxy.aclose()


app = FastAPI(lifespan=close_proxy_event)


def authenticate_user(username: str, password: str) -> bool:
    p = pam.pam()
    return p.authenticate(username, password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(request: Request):
    token = request.cookies.get("hpm_access_token")
    if token is None:
        return RedirectResponse(url="/login", status_code=303)
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


@app.get("/login", response_class=HTMLResponse)
async def login():
    return HTMLResponse(
        """
        <form action="/token" method="post">
        <label for="username">Username:</label>
        <input type="text" id="username" name="username" required />
        <label for="password">Password:</label>
        <input type="password" id="password" name="password" required />
        <button type="submit">Login</button>
        </form>
        """
    )


@app.post("/token", response_class=RedirectResponse)
async def login_for_access_token(
    response: Response, username: str = Form(...), password: str = Form(...)
):
    if authenticate_user(username, password):
        response = RedirectResponse("/", status_code=303)
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        hpm_access_token = create_access_token(
            data={"sub": username}, expires_delta=access_token_expires
        )
        response.set_cookie(
            key="hpm_access_token",
            value=hpm_access_token,
            httponly=True,
        )
        return response
    else:
        return RedirectResponse(url="/login", status_code=303)

@app.get("/")
async def root(request: Request):
    try:
        user = await get_current_user(request)
    except HTTPException:
        return RedirectResponse(url="/login", status_code=303)
    return RedirectResponse(f"/{user}")

@app.api_route("/{user_path}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH", "TRACE"])
async def proxy(request: Request, user_path: str, path: str = ""):
    user = await get_current_user(request)

    if user_path != user:
        return RedirectResponse(url="/login", status_code=303)

    if user not in containers:
        containers[user] = Spawner(user)

    host = containers[user].get_internal_ip()
    if user not in proxies:
        target_url = f"http://{host}:8787/"
        proxies[user] = ReverseHttpProxy(AsyncClient(), base_url=target_url)
    
    res = await proxies[user].proxy(request=request, path=path)

    if "location" in res.headers:
        res.headers["location"] = res.headers["location"].replace(f"http://{host}:8787", f"/{user}")
    
    return res


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=6006, reload=True)
