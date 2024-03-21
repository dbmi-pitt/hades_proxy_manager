from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from src import instances
from src.utils.auth import get_current_user

router = APIRouter(prefix="", tags=["proxy"])


@router.api_route(
    "/{user_path}/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH", "TRACE"],
)
async def proxy(request: Request, user_path: str, path: str = ""):
    username = await get_current_user(request)

    if (
        (type(username) is not str)
        or (user_path != username)
        or (username not in instances)
    ):
        return RedirectResponse(url="/_/login", status_code=303)

    if instances[username].container.state != "running":
        try:
            instances[username].container.spawn()
        except Exception as e:
            return {"error": f"Container error: {e}"}
    else:
        instances[username].container.update_last_used()

    try:
        res = await instances[username].proxy.proxy(request=request, path=path)
    except Exception as e:
        return {"error": f"Proxy error: {e}"}

    if "location" in res.headers:
        res.headers["location"] = res.headers["location"].replace(
            f"http://{instances[username].container.internal_host}", f"/{username}"
        )

    return res
