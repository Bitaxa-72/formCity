from pathlib import Path

import pytest

from app.core.config import ConfigError, Settings, normalize_proxy_url, parse_allowed_usernames, parse_bool, parse_env_file


def test_parse_env_file_trims_keys_and_values(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "SAMPLE_NAME = value ",
                "SAMPLE_URL = socks5://placeholder",
                "EMPTY_LINE_BELOW=",
                "",
                "# comment",
            ],
        ),
        encoding="utf-8",
    )

    values = parse_env_file(env_file)

    assert values["SAMPLE_NAME"] == "value"
    assert values["SAMPLE_URL"] == "socks5://placeholder"
    assert values["EMPTY_LINE_BELOW"] == ""


def test_parse_allowed_usernames_normalizes_values() -> None:
    assert parse_allowed_usernames("@UserOne, userTwo USERTHREE") == {
        "userone",
        "usertwo",
        "userthree",
    }


def test_parse_allowed_usernames_supports_json_list() -> None:
    assert parse_allowed_usernames('["@UserOne", "userTwo", "USERTHREE"]') == {
        "userone",
        "usertwo",
        "userthree",
    }


def test_settings_safe_summary_counts_admins() -> None:
    settings = Settings(
        bot_token="placeholder-token",
        database_url="sqlite:///placeholder.db",
        openai_key="placeholder-key",
        openai_model="model",
        proxy="socks5://placeholder",
        allowed_usernames={"tester"},
        admin_usernames={"admin"},
    )

    summary = settings.safe_summary()

    assert summary["admin_usernames_count"] == 1


def test_parse_bool() -> None:
    assert parse_bool("true", False) is True
    assert parse_bool("0", True) is False
    assert parse_bool(None, True) is True


def test_parse_bool_rejects_unknown_value() -> None:
    with pytest.raises(ConfigError):
        parse_bool("maybe", False)


def test_normalize_proxy_url_uses_remote_socks_dns() -> None:
    assert normalize_proxy_url("socks5://proxy.example:1080") == "socks5h://proxy.example:1080"
    assert normalize_proxy_url("http://proxy.example:8080") == "http://proxy.example:8080"


def test_settings_validate_required() -> None:
    settings = Settings(
        bot_token="token",
        database_url="sqlite:///test.db",
        openai_key="openai",
        openai_model="model",
        proxy="proxy",
        allowed_usernames={"tester"},
    )

    settings.validate_required()


def test_settings_validate_required_rejects_missing_values() -> None:
    settings = Settings(bot_token=None, allowed_usernames=set())

    with pytest.raises(ConfigError):
        settings.validate_required()


def test_settings_safe_summary_hides_secrets() -> None:
    settings = Settings(
        bot_token="placeholder-token",
        database_url="sqlite:///placeholder.db",
        openai_key="placeholder-key",
        tavily_key="placeholder-tavily",
        openai_model="model",
        proxy="socks5://placeholder",
        allowed_usernames={"tester"},
    )

    summary = settings.safe_summary()

    assert summary["bot_token"] is True
    assert summary["openai_key"] is True
    assert summary["tavily_key"] is True
    assert summary["proxy"] is True
    assert summary["database_url"] is True
    assert "placeholder-token" not in str(summary)
    assert "placeholder-key" not in str(summary)
    assert "socks5://placeholder" not in str(summary)
    assert "sqlite:///placeholder.db" not in str(summary)
