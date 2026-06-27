import asyncio
import json

from fastapi.encoders import jsonable_encoder

from app.bot.sending import safe_send_message
from app.bot.telegram_client import TelegramClient
from app.bot.telegram_response import split_telegram_text
from app.core.access import normalize_username
from app.core.config import Settings


ADMIN_DEBUG_TASKS: set[asyncio.Task[None]] = set()


def is_admin_debug_enabled(username: str | None, settings: Settings, state: dict[str, object] | None) -> bool:
    normalized_username = normalize_username(username)
    return bool(
        normalized_username
        and normalized_username in settings.admin_usernames
        and state
        and state.get("admin_debug_enabled") is True
    )


async def send_admin_debug_now(
    telegram_client: TelegramClient,
    chat_id: int,
    request_id: str,
    enabled: bool,
    stage: str,
    payload: object,
) -> None:
    if not enabled:
        return

    body = json.dumps(jsonable_encoder(payload), ensure_ascii=False, indent=2)
    text = f"ADMIN DEBUG: {stage}\nrequest_id: {request_id}\n\n```json\n{body}\n```"
    for chunk in split_telegram_text(text):
        await safe_send_message(telegram_client, chat_id, chunk, request_id)


async def send_admin_debug(
    telegram_client: TelegramClient,
    chat_id: int,
    request_id: str,
    enabled: bool,
    stage: str,
    payload: object,
) -> None:
    if not enabled:
        return

    task = asyncio.create_task(
        send_admin_debug_now(telegram_client, chat_id, request_id, enabled, stage, payload),
    )
    ADMIN_DEBUG_TASKS.add(task)
    task.add_done_callback(ADMIN_DEBUG_TASKS.discard)
