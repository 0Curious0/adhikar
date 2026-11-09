from pathlib import Path
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    gnani_api_key: str
    gnani_base_url: str = "https://api.vachana.ai"
    sarvam_api_key: str
    profile_db_path: Path = Path("var/profiles.db")
    # `NoDecode` is required here: pydantic-settings' env source otherwise tries to JSON-decode
    # every list-typed env var *before* field validators ever run, so a plain comma-separated
    # string (not JSON array syntax) would hard-crash app startup with a JSONDecodeError rather
    # than reaching `_split_comma_separated_origins` below at all — confirmed by actually setting
    # the env var and starting the app, not just constructing Settings() with a kwarg directly
    # (which bypasses the env source's decoding step and so doesn't exercise this bug at all).
    allowed_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    """CORS origins the frontend is served from. Defaults to Vite's local dev origins, so no
    .env change is needed for local development. In production (e.g. a Vercel-hosted frontend),
    set ALLOWED_ORIGINS to a comma-separated list, e.g.
    "https://adhikar.vercel.app,https://adhikar-git-main.vercel.app" — plain comma-separated,
    not JSON array syntax, since that's what's actually easy to paste into a host's dashboard
    env-var field."""

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _split_comma_separated_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


# tells that settings can be either a Settings object or None, and initializes it to None
_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
