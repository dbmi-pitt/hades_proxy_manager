from datetime import UTC, datetime, timedelta
from typing import Optional

import jwt
from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse
from pam import pam
from starlette.requests import Request

from src import settings

JWT_ALGORITHM = "HS256"


def authenticate_user(username: str, password: str) -> bool:
    return pam().authenticate(username, password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=JWT_ALGORITHM
    )
    return encoded_jwt


async def get_current_user(request: Request):
    token = request.cookies.get("hpm_access_token")
    if token is None:
        return RedirectResponse(url="/_/login", status_code=303)
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub", None)
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
