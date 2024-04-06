from fastapi_proxy_lib.core.http import ReverseHttpProxy
from pydantic import BaseModel


class User(BaseModel):
    username: str


from src.core.container import Container


class Instance:
    def __init__(self, user: User, container: Container, proxy: ReverseHttpProxy):
        self.user = user
        self.container = container
        self.proxy = proxy
