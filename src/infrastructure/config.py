from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Short URL Service"
    debug: bool = False
    api_prefix: str = ""

    cors_allow_origins: str = Field(
        default="http://localhost:3000,http://localhost:8000",
        validation_alias="CORS_ALLOW_ORIGINS",
    )
    cors_allow_credentials: bool = Field(
        default=False, validation_alias="CORS_ALLOW_CREDENTIALS"
    )

    database_url: str = Field(..., validation_alias="DATABASE_URL")

    redis_host: str = Field(default="localhost", validation_alias="REDIS_HOST")
    redis_port: int = Field(default=6379, validation_alias="REDIS_PORT")
    redis_db: int = Field(default=0, validation_alias="REDIS_DB")
    redis_url: str = Field(
        default="redis://localhost:6379/0", validation_alias="REDIS_URL"
    )

    jwt_secret: str = Field(..., validation_alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")
    jwt_expiration: int = Field(default=3600, validation_alias="JWT_EXPIRATION")

    short_code_length: int = Field(default=6, validation_alias="SHORT_CODE_LENGTH")
    short_url_base: str = Field(
        default="http://localhost:8000", validation_alias="SHORT_URL_BASE"
    )

    cookie_secure: bool = Field(default=True, validation_alias="COOKIE_SECURE")
    cookie_httponly: bool = Field(default=True, validation_alias="COOKIE_HTTPONLY")
    cookie_samesite: str = Field(default="lax", validation_alias="COOKIE_SAMESITE")
    cookie_domain: str | None = Field(default=None, validation_alias="COOKIE_DOMAIN")
    access_token_cookie_name: str = Field(
        default="access_token", validation_alias="ACCESS_TOKEN_COOKIE_NAME"
    )
    refresh_token_cookie_name: str = Field(
        default="refresh_token", validation_alias="REFRESH_TOKEN_COOKIE_NAME"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
