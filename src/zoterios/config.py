"""Configuration management using pydantic-settings."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_settings: "Settings | None" = None


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_prefix="ZOTERIOS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    base_url: str = "http://localhost:23119"
    cache_dir: Path = Path.home() / ".cache" / "zoterios"
    http_proxy: str = ""
    https_proxy: str = ""


def get_settings(
    base_url: str | None = None,
    cache_dir: Path | None = None,
) -> Settings:
    """Return a cached singleton Settings instance.

    Optional *base_url* and *cache_dir* overrides are applied on first call
    (typically from CLI flags like ``--base-url`` / ``--cache-dir``).
    """
    global _settings
    if _settings is None:
        overrides: dict[str, str | Path] = {}
        if base_url is not None:
            overrides["base_url"] = base_url
        if cache_dir is not None:
            overrides["cache_dir"] = cache_dir
        _settings = Settings(**overrides)  # type: ignore[arg-type]
    return _settings
