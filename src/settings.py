from os import getenv

from pydantic_settings import BaseSettings


class _Settings(BaseSettings):
    JWT_SECRET_KEY: str = getenv("JWT_SECRET_KEY", "HADES_PROXY_MANAGER")
    JWT_EXPIRE_MINUTES: int = int(getenv("JWT_EXPIRE_MINUTES", 60))

    HADES_PORT: int = int(getenv("HADES_PORT", 8787))

    PORT: int = int(getenv("PORT", 6006))


settings = _Settings()
