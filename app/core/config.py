import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.access import normalize_username


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Settings:
    bot_token: str | None
    allowed_usernames: set[str]
    admin_usernames: set[str] = field(default_factory=set)
    database_url: str = "sqlite:///./formcity.db"
    openai_key: str | None = None
    tavily_key: str | None = None
    openai_model: str | None = None
    proxy: str | None = None
    telegram_proxy: str | None = None
    app_env: str = "local"
    allow_username_allowlist_fallback: bool = False
    allow_empty_allowlist: bool = False
    verified_answers_only: bool = True

    def validate_required(self) -> None:
        missing = []
        if not self.bot_token:
            missing.append("BOT_TOKEN")
        if not self.openai_key:
            missing.append("OPENAI_KEY")
        if not self.openai_model:
            missing.append("OPENAI_MODEL")
        if not self.proxy:
            missing.append("PROXY")
        if not self.allowed_usernames and not self.allow_empty_allowlist:
            missing.append("ALLOWED_USERNAMES")

        if missing:
            raise ConfigError(f"Missing required config values: {', '.join(missing)}")

    def safe_summary(self) -> dict[str, Any]:
        return {
            "app_env": self.app_env,
            "bot_token": bool(self.bot_token),
            "openai_key": bool(self.openai_key),
            "tavily_key": bool(self.tavily_key),
            "openai_model": self.openai_model,
            "proxy": bool(self.proxy),
            "telegram_proxy": bool(self.telegram_proxy),
            "database_url": bool(self.database_url),
            "allowed_usernames_count": len(self.allowed_usernames),
            "admin_usernames_count": len(self.admin_usernames),
            "allow_username_allowlist_fallback": self.allow_username_allowlist_fallback,
            "allow_empty_allowlist": self.allow_empty_allowlist,
            "verified_answers_only": self.verified_answers_only,
        }


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("\"'")

    return values


def parse_allowed_usernames(value: str | None) -> set[str]:
    if not value:
        return set()

    raw_items = value.replace("\n", ",").replace(" ", ",").split(",")
    return {
        normalized
        for item in raw_items
        if (normalized := normalize_username(item))
    }


def parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False

    raise ConfigError(f"Invalid boolean value: {value}")


def get_config_value(values: dict[str, str], key: str) -> str | None:
    value = os.getenv(key, values.get(key))
    return value.strip() if value else None


def normalize_proxy_url(value: str | None) -> str | None:
    if not value:
        return None

    proxy = value.strip()
    if proxy.startswith("socks5://"):
        return "socks5h://" + proxy[len("socks5://") :]
    return proxy


def load_settings() -> Settings:
    env_file_values = parse_env_file(Path(".env"))

    settings = Settings(
        bot_token=get_config_value(env_file_values, "BOT_TOKEN"),
        openai_key=get_config_value(env_file_values, "OPENAI_KEY"),
        tavily_key=get_config_value(env_file_values, "TAVILY_KEY"),
        openai_model=get_config_value(env_file_values, "OPENAI_MODEL"),
        proxy=normalize_proxy_url(get_config_value(env_file_values, "PROXY")),
        telegram_proxy=normalize_proxy_url(get_config_value(env_file_values, "TELEGRAM_PROXY")),
        database_url=get_config_value(env_file_values, "DATABASE_URL") or "sqlite:///./formcity.db",
        allowed_usernames=parse_allowed_usernames(
            get_config_value(env_file_values, "ALLOWED_USERNAMES"),
        ),
        admin_usernames=parse_allowed_usernames(
            get_config_value(env_file_values, "ADMIN_USERNAMES"),
        ),
        app_env=get_config_value(env_file_values, "APP_ENV") or "local",
        allow_username_allowlist_fallback=parse_bool(
            get_config_value(env_file_values, "ALLOW_USERNAME_ALLOWLIST_FALLBACK"),
            False,
        ),
        allow_empty_allowlist=parse_bool(
            get_config_value(env_file_values, "ALLOW_EMPTY_ALLOWLIST"),
            False,
        ),
        verified_answers_only=parse_bool(
            get_config_value(env_file_values, "VERIFIED_ANSWERS_ONLY"),
            True,
        ),
    )
    settings.validate_required()
    return settings
