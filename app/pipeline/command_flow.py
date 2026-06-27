import logging

from fastapi.encoders import jsonable_encoder

from app.bot.commands import ADMIN_DISABLED_MESSAGE, ADMIN_ENABLED_MESSAGE, ADMIN_ONLY_MESSAGE, COMMAND_RESPONSES
from app.bot.sending import safe_send_message
from app.bot.telegram_client import TelegramClient
from app.core.access import normalize_username
from app.core.config import Settings
from app.db.repositories import UserSessionRepository
from app.pipeline.session_state import clear_state_preserving_admin_debug


logger = logging.getLogger("formcity.webhook")


async def handle_bot_command(
    command: str | None,
    *,
    username: str | None,
    chat_id: int,
    update_id: int,
    request_id: str,
    user_id: int,
    current_state: dict[str, object],
    settings: Settings,
    telegram_client: TelegramClient,
    user_session_repository: UserSessionRepository,
) -> dict[str, object] | None:
    if not command:
        return None

    if command == "/admin":
        normalized_username = normalize_username(username)
        if not normalized_username or normalized_username not in settings.admin_usernames:
            await safe_send_message(
                telegram_client,
                chat_id,
                ADMIN_ONLY_MESSAGE,
                request_id,
            )
            return {
                "ok": True,
                "request_id": request_id,
                "access": "allowed",
                "command": command,
                "admin": "denied",
                "session": "loaded",
            }

        state_to_save = dict(current_state)
        admin_debug_enabled = not bool(state_to_save.get("admin_debug_enabled"))
        state_to_save["admin_debug_enabled"] = admin_debug_enabled
        user_session_repository.save_dialog_state(
            user_id,
            jsonable_encoder(state_to_save),
        )
        await safe_send_message(
            telegram_client,
            chat_id,
            ADMIN_ENABLED_MESSAGE if admin_debug_enabled else ADMIN_DISABLED_MESSAGE,
            request_id,
        )
        return {
            "ok": True,
            "request_id": request_id,
            "access": "allowed",
            "command": command,
            "admin_debug_enabled": admin_debug_enabled,
            "session": "loaded",
        }

    if command in {"/clear", "/start"}:
        clear_state_preserving_admin_debug(
            user_session_repository,
            user_id,
            current_state,
        )

    await safe_send_message(
        telegram_client,
        chat_id,
        COMMAND_RESPONSES[command],
        request_id,
    )
    logger.info(
        "command_handled request_id=%s update_id=%s chat_id=%s username=%s command=%s",
        request_id,
        update_id,
        chat_id,
        username,
        command,
    )
    return {
        "ok": True,
        "request_id": request_id,
        "access": "allowed",
        "command": command,
        "session": "loaded",
    }
