from os import getenv

from pydantic_settings import BaseSettings


class _Settings(BaseSettings):
    JWT_SECRET_KEY: str = getenv("HPM_JWT_SECRET_KEY", "HADES_PROXY_MANAGER")
    JWT_EXPIRE_MINUTES: int = int(getenv("HPM_JWT_EXPIRE_MINUTES", 60))

    HADES_PORT: int = int(getenv("HPM_HADES_PORT", 8787))

    PREFIX: str = getenv("HPM_PREFIX", "/hpm")
    PORT: int = int(getenv("HPM_PORT", 6006))


settings = _Settings()
