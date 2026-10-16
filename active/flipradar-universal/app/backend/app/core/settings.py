"""Isolated backend configuration."""

from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="FLIP_BACKEND_",
        extra="ignore",
        env_file=None,
    )

    environment: Literal[
        "development", "test", "production"
    ] = "development"

    database_url: str
    redis_url: str = "redis://127.0.0.1:6379/2"
    signing_secret: SecretStr | None = None

    @model_validator(mode="after")
    def check_configuration(self):
        if not self.database_url.startswith(
            "postgresql+psycopg://"
        ):
            raise ValueError(
                "Backend requires postgresql+psycopg URL"
            )

        if self.environment == "production":
            secret = (
                self.signing_secret.get_secret_value()
                if self.signing_secret
                else ""
            )

            if (
                len(secret) < 32
                or secret.lower() in {
                    "change-me", "test", "example"
                }
            ):
                raise ValueError(
                    "Production signing secret missing/unsafe"
                )

        return self
